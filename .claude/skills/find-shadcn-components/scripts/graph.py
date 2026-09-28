#!/usr/bin/env python3
"""Navigate the component graph (Domain -> Category -> Item -> Registry) from local files.

    graph.py domains                               top-level areas with sizes
    graph.py categories [--domain D3] [--grep chart] [--top 40]
    graph.py category "Kanban Board" [--kind component] [--per-registry 3]
                                                   every registry's implementation of one type
    graph.py similar @reui/c-kanban-1 [--k 12] [--other-registries]
                                                   nearest items by embedding (offline, no API call)
    graph.py registry @reui                        what a registry covers, by category
Add --json to any command for machine-readable output.

Reads data/graph/*.json (built by scripts/build_graph.py, committed) + data/registries.enriched.json;
`similar` also needs data/embeddings/search_vectors_1024.npy + items.json (python scripts/fetch_data.py).
"""
import argparse, json, os, re, sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
G = os.path.join(ROOT, "data", "graph")
EMB = os.path.join(ROOT, "data", "embeddings")
DEMO = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)


def load(name):
    return json.load(open(os.path.join(G, name)))


def items_index():
    idx = {}
    for r in json.load(open(os.path.join(ROOT, "data", "registries.enriched.json")))["registries"]:
        for it in r["components"]["items"]:
            idx[f'{r["handle"]}/{it["name"]}'] = {**it, "handle": r["handle"],
                                                  "registryHealth": (r.get("health") or {}).get("status"),
                                                  "stale": bool(r["components"].get("stale"))}
    return idx


def row(iid, it, extra=""):
    link = it.get("url") or f'(no page: {it.get("linkMethod")})'
    flag = " ⚠ stale" if it.get("stale") else (" ⚠ unavailable" if it.get("registryHealth") == "unavailable" else "")
    return (f'  npx shadcn add {iid}  [{it.get("kind") or it.get("type")}]{extra}{flag}\n'
            f'      {(it.get("description") or "")[:150]}\n      {link}')


def find_category(cats, q):
    ql = q.lower()
    exact = [c for c in cats if c["id"].lower() == ql or c["label"].lower() == ql]
    if exact:
        return exact[0], []
    part = sorted([c for c in cats if ql in c["label"].lower()], key=lambda c: -c["itemCount"])
    return (part[0], part[1:8]) if part else (None, [])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["domains", "categories", "category", "similar", "registry"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--domain")
    ap.add_argument("--grep")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--kind", default="")
    ap.add_argument("--per-registry", type=int, default=3)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--other-registries", action="store_true")
    ap.add_argument("--include-demos", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out = lambda obj: print(json.dumps(obj, indent=1, ensure_ascii=False))

    doms = {d["id"]: d for d in load("domains.json")}
    cats = load("categories.json")

    if a.cmd == "domains":
        rows = sorted(doms.values(), key=lambda d: -d["itemCount"])
        if a.json: return out(rows)
        for d in rows:
            print(f'{d["id"]:<4} {d["itemCount"]:>6} items  {d["nCategories"]:>3} cats  {d["label"]} — {d["description"]}')
        return

    if a.cmd == "categories":
        rows = [c for c in cats if (not a.domain or c["domainId"] == a.domain)
                and (not a.grep or a.grep.lower() in (c["label"] + " " + c["description"]).lower())][:a.top]
        if a.json: return out(rows)
        for c in rows:
            print(f'{c["id"]:<6} {c["itemCount"]:>5} items / {c["registryCount"]:>3} registries  '
                  f'{c["label"]}  [{doms.get(c["domainId"], {}).get("label", "?")}] — {c["description"]}')
        return

    item_cat = load("item_categories.json")
    idx = items_index()
    kinds = {k for k in a.kind.split(",") if k}
    keep = lambda iid: iid in idx and (a.include_demos or not DEMO.search(iid)) \
        and (not kinds or idx[iid].get("kind") in kinds)

    if a.cmd == "category":
        c, alts = find_category(cats, a.arg or "")
        if not c:
            sys.exit(f'no category matching "{a.arg}" — try: graph.py categories --grep {a.arg}')
        by_reg = defaultdict(list)
        for iid, cid in item_cat.items():
            if cid == c["id"] and keep(iid):
                by_reg[iid.split("/", 1)[0]].append(iid)
        if a.json:
            return out({"category": c, "registries": {h: [{"id": i, **idx[i]} for i in v[:a.per_registry]]
                                                      for h, v in by_reg.items()}})
        print(f'{c["id"]} {c["label"]} — {c["description"]}\n'
              f'{sum(map(len, by_reg.values()))} items from {len(by_reg)} registries'
              + (f' · other matches: {", ".join(x["label"] for x in alts)}' if alts else "") + "\n")
        for h, v in sorted(by_reg.items(), key=lambda x: -len(x[1])):
            print(f"{h}  ({len(v)})")
            for iid in v[:a.per_registry]:
                print(row(iid, idx[iid]))
        return

    if a.cmd == "registry":
        h = a.arg if (a.arg or "").startswith("@") else f"@{a.arg}"
        reg = next((r for r in load("registries.json") if r["handle"] == h), None)
        if not reg:
            sys.exit(f"unknown registry {h}")
        cov = Counter(cid for iid, cid in item_cat.items() if iid.startswith(h + "/"))
        cl = {c["id"]: c for c in cats}
        rows = [{"category": cl[cid]["label"], "id": cid, "items": n} for cid, n in cov.most_common()]
        if a.json: return out({"registry": reg, "categories": rows})
        print(f'{h} — {reg["description"]}\n  {reg["componentCount"]} items · health {reg["health"]} · '
              f'{"active" if reg["active"] else "INACTIVE"} · {reg["browseUrl"]}\n')
        for r_ in rows[:a.top]:
            print(f'  {r_["items"]:>4}  {r_["category"]}  ({r_["id"]})')
        return

    if a.cmd == "similar":
        import numpy as np
        emb_items = json.load(open(os.path.join(EMB, "items.json")))
        V = np.load(os.path.join(EMB, "search_vectors_1024.npy"))
        uidx = {it["id"]: it["uidx"] for it in emb_items}
        if a.arg not in uidx:
            sys.exit(f"{a.arg} not in the search index (format @handle/name; run scripts/fetch_data.py?)")
        q = V[uidx[a.arg]].astype(np.float32)
        sims = V.astype(np.float32) @ q
        src_reg = a.arg.split("/", 1)[0]
        res, seen = [], set()
        # uidx -> item ids (dedup texts share a vector)
        by_u = defaultdict(list)
        for it in emb_items:
            by_u[it["uidx"]].append(it["id"])
        for u in np.argsort(-sims)[:5000]:
            for iid in by_u[int(u)]:
                reg = iid.split("/", 1)[0]
                key = (reg, iid.split("/")[-1])
                if iid == a.arg or key in seen or not keep(iid) or (a.other_registries and reg == src_reg):
                    continue
                seen.add(key)
                res.append((float(sims[u]), iid))
            if len(res) >= a.k:
                break
        res = res[:a.k]
        if a.json: return out([{"id": i, "cosine": round(s, 3), **idx[i]} for s, i in res])
        print(f"nearest to {a.arg}:\n")
        for s, iid in res:
            print(row(iid, idx[iid], f"  cos={s:.3f}"))


if __name__ == "__main__":
    main()
