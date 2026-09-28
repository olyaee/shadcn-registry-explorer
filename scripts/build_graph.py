#!/usr/bin/env python3
"""
Assemble the component graph from clusters + labels (+ embeddings for the optional Neo4j export).

Hierarchy: Domain -> Category -> Item -> Registry
  Domain / Category : unsupervised clusters (scripts/cluster_*.py) named by scripts/label_clusters.py
  Item / Registry   : data/registries.enriched.json

Outputs (small, committed — the graph the find-shadcn-components skill's graph.py reads):
  data/graph/domains.json          [{id, label, description, itemCount, nCategories}]
  data/graph/categories.json       [{id, label, description, domainId, itemCount, registryCount}]
  data/graph/registries.json       [{handle, name, homepage, health, active, browseUrl, ...}]
  data/graph/item_categories.json  {"@handle/name": "C123", ...}
  data/graph/meta.json
With --neo4j also (git-ignored, for scripts/load_neo4j.py):
  data/graph/items.jsonl, data/graph/item_vectors.npy  (1024-d search vectors)

Usage: python scripts/build_graph.py [--neo4j]
"""
import json, glob, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
os.makedirs("data/graph", exist_ok=True)
NEO4J = "--neo4j" in sys.argv

enr = json.load(open("data/registries.enriched.json"))
enr_items = {}
for r in enr["registries"]:
    for it in r["components"]["items"]:
        if it.get("name"):
            enr_items[f'{r["handle"]}/{it["name"]}'] = it
items_meta = json.load(open("data/embeddings/items.json"))
cats_raw = json.load(open("data/clusters/categories.json"))
uidx2cluster = {int(k): v for k, v in cats_raw["uidxToCluster"].items()}
cat_meta = {c["cluster"]: c for c in cats_raw["clusters"]}
dom = json.load(open("data/clusters/domains.json"))
cat2dom = {int(k): v for k, v in dom["catToDomain"].items()}
dom_labels = json.load(open("data/clusters/domain_labels.json"))

# ---- category labels (fallback: the clusterer's name guess) ----
cat_label = {}
for fp in sorted(glob.glob("data/clusters/labels/output_*.json")):
    for row in json.load(open(fp)):
        cat_label[int(row["cluster"])] = {"label": row["label"], "description": row.get("description", "")}
missing = [c for c in cat_meta if c not in cat_label]
if missing:
    print(f"  ! {len(missing)} categories missing labels -> using guess")
    for c in missing:
        cat_label[c] = {"label": cat_meta[c]["label_guess"].title(), "description": ""}

# ---- merge clusters that received the same label (one component type split by the clusterer) ----
by_label = {}
for cid in sorted(cat_meta, key=lambda c: -cat_meta[c]["itemCount"]):
    by_label.setdefault(cat_label[cid]["label"].lower(), []).append(cid)
canon = {cid: grp[0] for grp in by_label.values() for cid in grp}     # largest cluster keeps its id
merged = {}
for grp in by_label.values():
    head = grp[0]
    merged[head] = {**cat_meta[head], "itemCount": sum(cat_meta[c]["itemCount"] for c in grp), "clusters": grp}
print(f"  categories: {len(cat_meta)} clusters -> {len(merged)} after merging same-label clusters")
cat_meta = merged

# ---- item -> category ----
item_cat = {it["id"]: f'C{canon[uidx2cluster[it["uidx"]]]}' for it in items_meta}
json.dump(item_cat, open("data/graph/item_categories.json", "w"), ensure_ascii=False, separators=(",", ":"))
regs_per_cat = defaultdict(set)
for iid, cid in item_cat.items():
    regs_per_cat[cid].add(iid.split("/", 1)[0])

# ---- Domains / Categories ----
domains = []
for d in dom["domains"]:
    did = str(d["domain"])
    lbl = dom_labels.get(did, {"label": f"Domain {did}", "description": ""})
    domains.append({"id": f"D{did}", "label": lbl["label"], "description": lbl["description"],
                    "itemCount": d["itemCount"], "nCategories": d["nCategories"]})
json.dump(domains, open("data/graph/domains.json", "w"), ensure_ascii=False, indent=1)

categories = []
for cid, c in sorted(cat_meta.items(), key=lambda x: -x[1]["itemCount"]):
    lab = cat_label[cid]
    categories.append({"id": f"C{cid}", "label": lab["label"], "description": lab["description"],
                       "domainId": f"D{cat2dom.get(cid)}", "itemCount": c["itemCount"],
                       "registryCount": len(regs_per_cat[f"C{cid}"])})
json.dump(categories, open("data/graph/categories.json", "w"), ensure_ascii=False, indent=1)

# ---- Registries ----
try:
    pages = json.load(open("data/raw/pages.json"))
except FileNotFoundError:
    pages = {}
registries = []
for r in enr["registries"]:
    c = r["components"]
    health = (r.get("health") or {}).get("status")
    pl = pages.get(r["handle"]) or []
    registries.append({"handle": r["handle"], "name": r["name"], "homepage": r["homepage"],
                       "description": r.get("description", ""), "framework": r.get("framework", "react"),
                       "terminology": c.get("terminology"), "componentCount": c["count"],
                       "hasComponents": c["found"], "listed": r.get("listed", True),
                       "health": health, "stale": bool(c.get("stale")),
                       "active": bool(r.get("listed", True) and health != "unavailable" and not c.get("stale")),
                       "browseUrl": pl[0]["url"] if pl else r["homepage"],
                       "links": [f'{l["label"]}: {l["url"]}' for l in pl]})
json.dump(registries, open("data/graph/registries.json", "w"), ensure_ascii=False, indent=1)

meta = {"nodes": {"domains": len(domains), "categories": len(categories),
                  "registries": len(registries), "items": len(items_meta)},
        "builtFrom": {"catalogue": enr.get("capturedAt"), "clusters": cats_raw.get("params")}}

# ---- optional Neo4j export ----
if NEO4J:
    import numpy as np
    V = np.load("data/embeddings/search_vectors_1024.npy")       # unique x 1024, normalised
    vecs = np.zeros((len(items_meta), V.shape[1]), dtype=np.float32)
    with open("data/graph/items.jsonl", "w") as f:
        for i, it in enumerate(items_meta):
            ei = enr_items.get(it["id"], {})
            f.write(json.dumps({"id": it["id"], "name": it["name"], "type": it["type"],
                                "description": ei.get("description") or it["description"],
                                "handle": it["handle"], "categoryId": item_cat[it["id"]],
                                "kind": ei.get("kind") or "", "category": ei.get("category") or "",
                                "tags": ei.get("tags") or [], "useCases": ei.get("useCases") or [],
                                "style": ei.get("style") or [], "viewUrl": ei.get("url"),
                                "linkMethod": ei.get("linkMethod"),
                                "descriptionOriginal": ei.get("descriptionOriginal") or ""},
                               ensure_ascii=False) + "\n")
            vecs[i] = V[it["uidx"]]
    np.save("data/graph/item_vectors.npy", vecs)
    meta["embeddingDim"] = int(V.shape[1])
    print(f"  neo4j export: items.jsonl + item_vectors.npy {vecs.shape}")

json.dump(meta, open("data/graph/meta.json", "w"), indent=2)
print("GRAPH BUILT:", json.dumps(meta["nodes"]))
