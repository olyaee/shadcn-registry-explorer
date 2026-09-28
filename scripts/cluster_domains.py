#!/usr/bin/env python3
"""
Domain layer: cluster the category centroids into top-level "big node" domains.
Count emerges from the data (HDBSCAN on centroids; noise -> nearest domain).
Writes data/clusters/domains.json.
"""
import json, argparse
import numpy as np
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("--n-domains", type=int, default=14)
args = ap.parse_args()

from sklearn.cluster import AgglomerativeClustering
cent = np.load("data/clusters/centroids.npy")            # 396 x 3072 (normalized)
cats = json.load(open("data/clusters/categories.json"))["clusters"]
cids = json.load(open("data/clusters/cluster_ids.json"))
id2cat = {c["cluster"]: c for c in cats}
try:   # prefer LLM category labels (scripts/label_clusters.py) in the printout
    import glob
    for fp in glob.glob("data/clusters/labels/output_*.json"):
        for row in json.load(open(fp)):
            if int(row["cluster"]) in id2cat:
                id2cat[int(row["cluster"])]["label_llm"] = row["label"]
except Exception:
    pass
print(f"category centroids: {cent.shape}")

# Agglomerative on centroids (cosine distance, average linkage) — stable & controllable.
final = AgglomerativeClustering(n_clusters=args.n_domains,
                                linkage="ward").fit_predict(cent)
dids = sorted(set(int(d) for d in final))
print(f"-> {len(dids)} domains")

# assemble domains
domains = {}
for pos, cid in enumerate(cids):          # cids aligned to centroid rows
    d = int(final[pos])
    domains.setdefault(d, []).append(id2cat[cid])

out = []
for d, catlist in domains.items():
    catlist.sort(key=lambda c: -c["itemCount"])
    out.append({
        "domain": d,
        "itemCount": sum(c["itemCount"] for c in catlist),
        "nCategories": len(catlist),
        "topCategoryLabels": [c.get("label_llm") or c["label_guess"] for c in catlist[:12]],
    })
out.sort(key=lambda x: -x["itemCount"])
json.dump({"nDomains": len(dids), "domains": out,
           "catToDomain": {str(cids[pos]): int(final[pos]) for pos in range(len(cids))}},
          open("data/clusters/domains.json", "w"), ensure_ascii=False, indent=2)

print(f"\n{len(out)} domains:")
for dm in out:
    print(f'  D{dm["domain"]:<3} {dm["itemCount"]:>6} items / {dm["nCategories"]:>3} cats  '
          f'| {", ".join(dm["topCategoryLabels"][:10])}')
