#!/usr/bin/env python3
"""
Category clustering (unsupervised): UMAP -> HDBSCAN on the item embeddings.
Noise points are assigned to their nearest cluster centroid (cosine) so every
item lands somewhere. Prints diagnostics; writes data/clusters/categories.json.

Usage: python scripts/cluster_categories.py [--min-cluster-size N] [--umap-dims D]
"""
import json, re, argparse, os
import numpy as np
from collections import Counter

def load():
    V = np.load("data/embeddings/unique_vectors.npy").astype(np.float32)   # stored float16
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-12
    texts = json.load(open("data/embeddings/unique_texts.json"))
    items = json.load(open("data/embeddings/items.json"))
    return V, texts, items

def norm_name(n):
    n = re.sub(r"[-_]v?\d+$", "", n or "")          # strip trailing -01, -v2
    n = re.sub(r"\d+$", "", n)
    return n.replace("-", " ").replace("_", " ").strip().lower()

def label_guess(names):
    normed = [norm_name(n) for n in names if n]
    c = Counter(normed)
    # prefer the most common full normalized name; fall back to most common token
    top = [w for w, _ in c.most_common(3) if w]
    if top and c.most_common(1)[0][1] >= max(2, 0.1 * len(names)):
        return top[0]
    toks = Counter(t for n in normed for t in n.split())
    return (toks.most_common(1)[0][0] if toks else "misc")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-cluster-size", type=int, default=15)
    ap.add_argument("--min-samples", type=int, default=5)
    ap.add_argument("--umap-dims", type=int, default=15)
    ap.add_argument("--neighbors", type=int, default=15)
    args = ap.parse_args()

    import umap, hdbscan
    V, texts, items = load()
    print(f"unique vectors: {V.shape}")

    cache = f"data/clusters/umap_{args.umap_dims}d_{args.neighbors}n_{V.shape[0]}.npy"   # keyed by corpus size
    if os.path.exists(cache):
        print(f"loading cached UMAP {cache}")
        X = np.load(cache)
    else:
        print("UMAP reducing 3072 ->", args.umap_dims, "...")
        reducer = umap.UMAP(n_neighbors=args.neighbors, n_components=args.umap_dims,
                            metric="cosine", min_dist=0.0, random_state=42)
        X = reducer.fit_transform(V)
        os.makedirs("data/clusters", exist_ok=True)
        np.save(cache, X)

    print(f"HDBSCAN (min_cluster_size={args.min_cluster_size}, min_samples={args.min_samples}) ...")
    clu = hdbscan.HDBSCAN(min_cluster_size=args.min_cluster_size,
                          min_samples=args.min_samples, metric="euclidean",
                          cluster_selection_method="eom")
    labels = clu.fit_predict(X)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise = int((labels == -1).sum())
    print(f"-> {n_clusters} clusters | noise: {noise} ({100*noise/len(labels):.1f}%)")

    # centroids in ORIGINAL normalized space for noise reassignment
    cids = sorted(c for c in set(labels) if c != -1)
    cent = np.zeros((len(cids), V.shape[1]), dtype=np.float32)
    for i, c in enumerate(cids):
        cent[i] = V[labels == c].mean(axis=0)
    cent /= (np.linalg.norm(cent, axis=1, keepdims=True) + 1e-9)

    final = labels.copy()
    noise_idx = np.where(labels == -1)[0]
    if len(noise_idx):
        sims = V[noise_idx] @ cent.T
        nearest = sims.argmax(axis=1)
        for k, ni in enumerate(noise_idx):
            final[ni] = cids[nearest[k]]

    # map unique-idx -> cluster; then items -> cluster via uidx
    uidx_to_cluster = {i: int(final[i]) for i in range(len(final))}

    # gather names per cluster (item-level, so popularity reflects real counts)
    names_by_cluster = {}
    itemcount_by_cluster = Counter()
    for it in items:
        c = uidx_to_cluster[it["uidx"]]
        names_by_cluster.setdefault(c, []).append(it["name"])
        itemcount_by_cluster[c] += 1

    clusters = []
    for c in cids:
        names = names_by_cluster.get(c, [])
        clusters.append({
            "cluster": int(c),
            "label_guess": label_guess(names),
            "itemCount": itemcount_by_cluster[c],
            "sampleNames": [n for n, _ in Counter(names).most_common(8)],
        })
    clusters.sort(key=lambda x: -x["itemCount"])

    os.makedirs("data/clusters", exist_ok=True)
    json.dump({
        "params": vars(args), "nClusters": n_clusters, "noiseReassigned": int(noise),
        "uidxToCluster": uidx_to_cluster, "clusters": clusters,
    }, open("data/clusters/categories.json", "w"), ensure_ascii=False)
    np.save("data/clusters/centroids.npy", cent)
    json.dump([int(c) for c in cids], open("data/clusters/cluster_ids.json", "w"))

    print(f"\nTop 25 clusters by item count:")
    for cl in clusters[:25]:
        print(f'  {cl["itemCount"]:>5}  [{cl["cluster"]:>3}] {cl["label_guess"]:<22} '
              f'e.g. {", ".join(cl["sampleNames"][:5])}')
    sizes = [cl["itemCount"] for cl in clusters]
    print(f"\nsize dist: max={max(sizes)} median={int(np.median(sizes))} "
          f"min={min(sizes)} | clusters<20 items: {sum(1 for s in sizes if s<20)}")

if __name__ == "__main__":
    main()
