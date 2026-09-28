#!/usr/bin/env python3
"""Hybrid (semantic + keyword) search over the local shadcn registry catalogue.

One ranked shortlist per concept. Each concept is scored two ways and fused with
Reciprocal Rank Fusion:
  - semantic : cosine between the query embedding (text-embedding-3-large, 1024d) and
               data/embeddings/search_vectors_1024.npy (built by scripts/embed_items.py)
  - keyword  : BM25 over name + category + tags + description (exact terms like "kanban")

Usage:
  python3 .claude/skills/find-shadcn-components/scripts/hybrid_search.py \
      "toggle between monthly and annual billing" "pricing card with feature list" [--k 8]
  python3 .../hybrid_search.py --brief brief.json      # {"concept": "query text", ...}

Options:
  --kind component,block    keep only these enriched kinds (component block hook page
                            template icon logo font theme utility); default: all
  --registry @a,@b          only these registries
  --per-registry 2          max results per registry per concept (diversity; 0 = no cap)
  --include-demos           keep *-demo / registry:example companion items (dropped by default)
  --keyword-only            skip embeddings (no network / no OPENAI_API_KEY)
  --json                    machine-readable output
"""
import argparse, json, math, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DATA = os.path.join(ROOT, "data", "registries.enriched.json")
EMB = os.path.join(ROOT, "data", "embeddings")
DEMO = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)
TOKEN = re.compile(r"[a-z0-9]+")
RRF_K = 60
POOL = 400            # top-N from each ranker that enter the fusion


def tokens(text):
    return TOKEN.findall((text or "").lower())


def load_docs(args):
    regs = json.load(open(DATA))["registries"]
    kinds = {k.strip() for k in args.kind.split(",") if k.strip()} if args.kind else None
    only = {r.strip() for r in args.registry.split(",") if r.strip()} if args.registry else None
    docs, seen = [], set()
    for r in regs:
        c = r.get("components") or {}
        if only and r["handle"] not in only:
            continue
        for it in c.get("items") or []:
            name = it.get("name") or ""
            if not args.include_demos and (DEMO.search(name) or it.get("type") == "registry:example"):
                continue
            if kinds and (it.get("kind") or "") not in kinds:
                continue
            # collapse style variants (fill/x, two-tone/x) onto one result per registry
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
                "framework": r.get("framework", "react"),
                "stale": bool(c.get("stale")),
            })
    return docs


class BM25:
    def __init__(self, docs, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.tf, self.len = [], []
        df = Counter()
        for d in docs:
            # name + category weighted x2: they are the most specific signals
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


def semantic(docs, queries):
    """cosine scores per query, or None when the index / API key is unavailable."""
    try:
        import numpy as np
        vec_path = os.path.join(EMB, "search_vectors_1024.npy")
        items = json.load(open(os.path.join(EMB, "items.json")))
        V = np.load(vec_path)
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(ROOT, ".env"))
        except ImportError:
            pass
        from openai import OpenAI
        if not os.getenv("OPENAI_API_KEY"):
            print(f"(no OPENAI_API_KEY in {ROOT}/.env — keyword ranking only)", file=sys.stderr)
            return None
        resp = OpenAI().embeddings.create(model="text-embedding-3-large", input=queries, dimensions=1024)
    except Exception as e:
        print(f"(semantic ranking unavailable: {type(e).__name__}: {str(e)[:120]} — keyword only)",
              file=sys.stderr)
        return None
    row = {it["id"]: it["uidx"] for it in items}
    idx = np.array([row.get(d["id"], -1) for d in docs])
    missing = int((idx < 0).sum())
    if missing:
        print(f"({missing} items are newer than the embedding index — rerun scripts/embed_items.py)",
              file=sys.stderr)
    M = V[np.clip(idx, 0, None)].astype(np.float32)
    Q = np.array([d.embedding for d in resp.data], dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    S = Q @ M.T
    S[:, idx < 0] = -1.0
    return S


def rank(docs, bm25, sem_row, query, k, per_reg):
    fused = defaultdict(float)
    lex = bm25.scores(query)
    lex_rank = sorted(lex, key=lex.get, reverse=True)[:POOL]
    for r, i in enumerate(lex_rank):
        fused[i] += 1 / (RRF_K + r + 1)
    cos = {}
    if sem_row is not None:
        import numpy as np
        top = np.argpartition(-sem_row, min(POOL, len(sem_row) - 1))[:POOL]
        top = top[np.argsort(-sem_row[top])]
        for r, i in enumerate(top):
            i = int(i); cos[i] = float(sem_row[i])
            fused[i] += 1 / (RRF_K + r + 1)
    for i in fused:                        # sink unreachable / stale / non-React registries
        if docs[i]["stale"] or docs[i]["health"] == "unavailable":
            fused[i] *= 0.6
        if docs[i]["framework"] != "react":
            fused[i] *= 0.5
    out, per = [], Counter()
    for i in sorted(fused, key=fused.get, reverse=True):
        d = docs[i]
        if per_reg and per[d["handle"]] >= per_reg:
            continue
        per[d["handle"]] += 1
        out.append({**d, "score": round(fused[i] * 1000, 2), "cosine": round(cos[i], 3) if i in cos else None,
                    "bm25": round(lex.get(i, 0.0), 2),
                    "install": f'npx shadcn add {d["handle"]}/{d["name"]}'})
        if len(out) >= k:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*")
    ap.add_argument("--brief", help='JSON {"piece": "query text", ...} file, or - for stdin')
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--kind", default="")
    ap.add_argument("--registry", default="")
    ap.add_argument("--per-registry", type=int, default=2)
    ap.add_argument("--include-demos", action="store_true")
    ap.add_argument("--keyword-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.brief:
        concepts = json.load(sys.stdin if args.brief == "-" else open(args.brief))
        if isinstance(concepts, list):                       # ["query", ...] also accepted
            concepts = {q: q for q in concepts}
    else:
        concepts = {q: q for q in args.queries}
    if not concepts:
        ap.error("give one or more queries, or --brief")
    docs = load_docs(args)
    bm25 = BM25(docs)
    S = None if args.keyword_only else semantic(docs, list(concepts.values()))

    results = {}
    for n, (concept, query) in enumerate(concepts.items()):
        results[concept] = rank(docs, bm25, None if S is None else S[n], query, args.k, args.per_registry)

    if args.json:
        print(json.dumps(results, indent=1, ensure_ascii=False))
        return 0
    print(f"{len(docs):,} items searched · {'hybrid (semantic + BM25)' if S is not None else 'keyword (BM25) only'}\n")
    for concept, rows in results.items():
        print(f"## {concept}" + (f"  — “{concepts[concept]}”" if concepts[concept] != concept else ""))
        for r in rows:
            flags = [f for f, on in (("stale", r["stale"]), ("unavailable", r["health"] == "unavailable"),
                                     (r["framework"], r["framework"] != "react")) if on]
            link = r["url"] if r["url"] else f'(no page: {r["linkMethod"]})'
            print(f'  {r["score"]:>5}  {r["install"]}  [{r["kind"] or r["type"]} · {r["category"]}]'
                  + (f'  cos={r["cosine"]}' if r["cosine"] is not None else "")
                  + (f'  ⚠ {", ".join(flags)}' if flags else ""))
            print(f'         {r["description"][:150]}')
            print(f'         {link}')
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
