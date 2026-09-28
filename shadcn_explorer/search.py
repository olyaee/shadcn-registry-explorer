"""Hybrid search: embedding cosine + BM25, fused with Reciprocal Rank Fusion.

The index (items, BM25, vectors) is built once per process and reused, so a long-lived
MCP server answers in milliseconds after the first call.
"""
import json, math, os, re, sys
from collections import Counter, defaultdict
from functools import lru_cache
from . import paths

DEMO = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)
TOKEN = re.compile(r"[a-z0-9]+")
RRF_K, POOL = 60, 400


def tokens(text):
    return TOKEN.findall((text or "").lower())


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b, self.tf, self.len = k1, b, [], []
        df = Counter()
        for d in docs:
            # name + category weighted x2: the most specific signals
            toks = (tokens(d["name"]) + tokens(d["category"])) * 2 + tokens(" ".join(d["tags"])) \
                + tokens(d["description"])
            c = Counter(toks)
            self.tf.append(c); self.len.append(len(toks)); df.update(c.keys())
        n = len(docs)
        self.avg = sum(self.len) / max(1, n)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.post = defaultdict(list)
        for i, c in enumerate(self.tf):
            for t in c:
                self.post[t].append(i)

    def scores(self, query):
        s = defaultdict(float)
        for t in set(tokens(query)):
            idf = self.idf.get(t)
            if not idf:
                continue
            for i in self.post[t]:
                f = self.tf[i][t]
                s[i] += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
        return s


@lru_cache(maxsize=1)
def index():
    """All items (style variants like fill/x collapsed onto one per registry) + BM25."""
    regs = json.load(open(paths.data("registries.enriched.json")))["registries"]
    docs, seen = [], set()
    for r in regs:
        c = r.get("components") or {}
        for it in c.get("items") or []:
            name = it.get("name") or ""
            key = (r["handle"], name.split("/")[-1])
            if key in seen:
                continue
            seen.add(key)
            docs.append({
                "id": f'{r["handle"]}/{name}', "handle": r["handle"], "name": name,
                "type": it.get("type", ""), "kind": it.get("kind", ""),
                "category": it.get("category", ""), "tags": it.get("tags") or [],
                "description": it.get("description") or "",
                "url": it.get("url"), "linkMethod": it.get("linkMethod"),
                "health": (r.get("health") or {}).get("status"),
                "framework": r.get("framework", "react"), "stale": bool(c.get("stale")),
                "demo": bool(DEMO.search(name) or it.get("type") == "registry:example"),
            })
    return docs, BM25(docs)


_VEC = None


def vectors():
    """(matrix aligned to index() docs, row mask) or None until the search index is downloaded.
    Only a successful load is cached, so a running server picks the index up once it lands."""
    global _VEC
    if _VEC is not None:
        return _VEC
    import numpy as np
    if not (paths.data("embeddings", "search_vectors_1024.npy").exists() and paths.data("embeddings", "items.json").exists()):
        return None
    V = np.load(paths.data("embeddings", "search_vectors_1024.npy"))
    row = {it["id"]: it["uidx"] for it in json.load(open(paths.data("embeddings", "items.json")))}
    docs, _ = index()
    idx = np.array([row.get(d["id"], -1) for d in docs])
    _VEC = (V[np.clip(idx, 0, None)].astype(np.float32), idx >= 0)
    return _VEC


def embed(queries):
    """Query embeddings, or (None, reason) when semantic ranking is unavailable."""
    paths.load_env()
    if not os.getenv("OPENAI_API_KEY"):
        return None, "no OPENAI_API_KEY — keyword ranking only"
    if vectors() is None:
        return None, "search index not downloaded yet — keyword ranking only"
    try:
        import numpy as np
        from openai import OpenAI
        resp = OpenAI().embeddings.create(model="text-embedding-3-large", input=queries, dimensions=1024)
        Q = np.array([d.embedding for d in resp.data], dtype=np.float32)
        return Q / np.linalg.norm(Q, axis=1, keepdims=True), None
    except Exception as e:
        return None, f"embedding failed ({type(e).__name__}) — keyword ranking only"


def search(concepts, kind=None, registry=None, k=8, per_registry=2, include_demos=False, keyword_only=False):
    """concepts: {piece: query} or [query]. Returns {"mode", "note", "results": {piece: [item...]}}."""
    if isinstance(concepts, (list, tuple)):
        concepts = {q: q for q in concepts}
    docs, bm25 = index()
    kinds = set(kind or [])
    regs = set(registry or [])
    keep = lambda d: (include_demos or not d["demo"]) and (not kinds or d["kind"] in kinds) \
        and (not regs or d["handle"] in regs)

    Q, note = (None, "keyword ranking only (requested)") if keyword_only else embed(list(concepts.values()))
    sims = None
    if Q is not None:
        M, mask = vectors()
        sims = Q @ M.T
        sims[:, ~mask] = -1.0

    import numpy as np
    out = {}
    for n, (piece, query) in enumerate(concepts.items()):
        fused, cos = defaultdict(float), {}
        lex = bm25.scores(query)
        for r, i in enumerate([i for i in sorted(lex, key=lex.get, reverse=True) if keep(docs[i])][:POOL]):
            fused[i] += 1 / (RRF_K + r + 1)
        if sims is not None:
            row = sims[n]
            top = np.argpartition(-row, min(POOL * 3, len(row) - 1))[:POOL * 3]
            top = [int(i) for i in top[np.argsort(-row[top])] if keep(docs[int(i)])][:POOL]
            for r, i in enumerate(top):
                cos[i] = float(row[i])
                fused[i] += 1 / (RRF_K + r + 1)
        for i in fused:                    # sink unreachable / stale / non-React registries
            d = docs[i]
            if d["stale"] or d["health"] == "unavailable":
                fused[i] *= 0.6
            if d["framework"] != "react":
                fused[i] *= 0.5
        rows, per = [], Counter()
        for i in sorted(fused, key=fused.get, reverse=True):
            d = docs[i]
            if per_registry and per[d["handle"]] >= per_registry:
                continue
            per[d["handle"]] += 1
            rows.append({**{k_: v for k_, v in d.items() if k_ != "demo"},
                         "score": round(fused[i] * 1000, 2), "cosine": round(cos[i], 3) if i in cos else None,
                         "install": f'npx shadcn add {d["handle"]}/{d["name"]}'})
            if len(rows) >= k:
                break
        out[piece] = rows
    return {"mode": "keyword" if sims is None else "hybrid", "note": note, "results": out}


def flags(r):
    return [f for f, on in (("stale", r.get("stale")), ("unavailable", r.get("health") == "unavailable"),
                            (r.get("framework"), r.get("framework", "react") != "react")) if on]


def format_text(res, concepts):
    lines = [f'{len(index()[0]):,} items · {"hybrid (semantic + keyword)" if res["mode"] == "hybrid" else "keyword only"}'
             + (f' — {res["note"]}' if res["note"] else ""), ""]
    for piece, rows in res["results"].items():
        q = concepts[piece] if isinstance(concepts, dict) else piece
        lines.append(f"## {piece}" + (f"  — “{q}”" if q != piece else ""))
        for r in rows:
            fl = flags(r)
            lines.append(f'  {r["score"]:>5}  {r["install"]}  [{r["kind"] or r["type"]} · {r["category"]}]'
                         + (f'  cos={r["cosine"]}' if r["cosine"] is not None else "")
                         + (f'  ⚠ {", ".join(fl)}' if fl else ""))
            lines.append(f'         {r["description"][:150]}')
            lines.append(f'         {r["url"] or "(no page: " + str(r["linkMethod"]) + ")"}')
        lines.append("")
    return "\n".join(lines)
