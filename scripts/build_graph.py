#!/usr/bin/env python3
"""
Assemble the knowledge graph from clusters + labels + embeddings.

Nodes:   Root, Domain(16), Category(396), Registry(238), Item(37,837)
Edges:   (Root)-[:HAS_DOMAIN]->(Domain)-[:HAS_CATEGORY]->(Category)-[:HAS_ITEM]->(Item)
         (Item)-[:PROVIDED_BY]->(Registry)
Vectors: item embeddings truncated 3072 -> 1024 dims (Matryoshka) + renormalized,
         saved aligned to items.jsonl for the Neo4j loader.

Outputs: data/graph/{domains,categories,registries}.json, items.jsonl,
         item_vectors_1024.npy, meta.json
"""
import json, glob, os
import numpy as np

os.makedirs("data/graph", exist_ok=True)
DIM = 1024

enr = json.load(open("data/registries.enriched.json"))
items_meta = json.load(open("data/embeddings/items.json"))
V = np.load("data/embeddings/unique_vectors.npy")               # unique x 3072 (normalized)
cats_raw = json.load(open("data/clusters/categories.json"))
uidx2cluster = {int(k): v for k, v in cats_raw["uidxToCluster"].items()}
cat_meta = {c["cluster"]: c for c in cats_raw["clusters"]}
dom = json.load(open("data/clusters/domains.json"))
cat2dom = {int(k): v for k, v in dom["catToDomain"].items()}
dom_labels = json.load(open("data/clusters/domain_labels.json"))

# ---- category labels (merge agent outputs; fallback to guess) ----
cat_label = {}
for fp in sorted(glob.glob("data/clusters/labels/output_*.json")):
    for row in json.load(open(fp)):
        cat_label[int(row["cluster"])] = {"label": row["label"],
                                          "description": row.get("description", "")}
missing = [c for c in cat_meta if c not in cat_label]
if missing:
    print(f"  ! {len(missing)} categories missing labels -> using guess")
    for c in missing:
        cat_label[c] = {"label": cat_meta[c]["label_guess"].title(), "description": ""}

# ---- truncate + renormalize embeddings to 1024 ----
Vt = V[:, :DIM].astype(np.float32)
Vt /= (np.linalg.norm(Vt, axis=1, keepdims=True) + 1e-9)

# ---- Domain nodes ----
domains = []
for d in dom["domains"]:
    did = str(d["domain"])
    lbl = dom_labels.get(did, {"label": f"Domain {did}", "description": ""})
    domains.append({"id": f"D{did}", "label": lbl["label"], "description": lbl["description"],
                    "itemCount": d["itemCount"], "nCategories": d["nCategories"]})
json.dump(domains, open("data/graph/domains.json", "w"), ensure_ascii=False, indent=1)

# ---- Category nodes ----
categories = []
for cid, c in cat_meta.items():
    lab = cat_label[cid]
    categories.append({"id": f"C{cid}", "label": lab["label"], "description": lab["description"],
                       "domainId": f'D{cat2dom.get(cid)}', "itemCount": c["itemCount"]})
json.dump(categories, open("data/graph/categories.json", "w"), ensure_ascii=False, indent=1)

# ---- Registry nodes (all 238) ----
registries = []
for r in enr["registries"]:
    c = r["components"]
    registries.append({"handle": r["handle"], "name": r["name"], "homepage": r["homepage"],
                       "terminology": c.get("terminology"), "componentCount": c["count"],
                       "hasComponents": c["found"]})
json.dump(registries, open("data/graph/registries.json", "w"), ensure_ascii=False, indent=1)

# ---- Item nodes + aligned vectors ----
vecs = np.zeros((len(items_meta), DIM), dtype=np.float32)
with open("data/graph/items.jsonl", "w") as f:
    for i, it in enumerate(items_meta):
        cluster = uidx2cluster[it["uidx"]]
        rec = {"id": it["id"], "name": it["name"], "type": it["type"],
               "description": it["description"], "handle": it["handle"],
               "categoryId": f"C{cluster}"}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        vecs[i] = Vt[it["uidx"]]
np.save("data/graph/item_vectors_1024.npy", vecs)

meta = {"nodes": {"domains": len(domains), "categories": len(categories),
                  "registries": len(registries), "items": len(items_meta)},
        "embeddingDim": DIM,
        "relationships_est": len(items_meta) * 2 + len(categories) + len(domains)}
json.dump(meta, open("data/graph/meta.json", "w"), indent=2)
print("GRAPH BUILT:", json.dumps(meta["nodes"]))
print(f"  vectors: {vecs.shape} ({DIM}d) | rel est: {meta['relationships_est']:,}")
