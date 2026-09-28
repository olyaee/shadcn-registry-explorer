#!/usr/bin/env python3
"""
Embed every registry item with OpenAI text-embedding-3-large.

- Input : data/registries.enriched.json  (items with name/type/description)
- Text  : "<human name> (<kind>): <description>"  per item
- Dedup : identical texts embedded once, reused (many items are just "button", etc.)
- Output: data/embeddings/{unique_vectors.npy (float16), unique_texts.json, items.json, meta.json}
          + search index for the find-shadcn-components skill's hybrid search:
            data/embeddings/search_vectors_1024.npy  (float16, first 1024 dims re-normalised
            — text-embedding-3 is Matryoshka-trained, same as the API's `dimensions=1024`)
- Cache : data/embeddings/cache.npz (text-hash -> vector) so re-runs only embed changed texts.

Usage:  python scripts/embed_items.py [--limit N] [--dry-run] [--workers 4]
"""
import os, json, sys, time, argparse, hashlib, threading, concurrent.futures
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
SEARCH_DIMS = 1024
CACHE = "data/embeddings/cache.npz"
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
DIMS = int(os.getenv("EMBEDDING_DIMENSIONS", "3072"))
# $/1M tokens (text-embedding-3-large = 0.13; -small = 0.02)
PRICE = {"text-embedding-3-large": 0.13, "text-embedding-3-small": 0.02}.get(MODEL, 0.13)

TYPE_KIND = {
    "registry:ui": "component", "registry:component": "component",
    "registry:block": "block", "registry:hook": "hook", "registry:page": "page",
    "registry:theme": "theme", "registry:style": "theme", "registry:icon": "icon",
    "registry:lib": "utility", "registry:font": "font", "registry:example": "example",
    "registry:file": "file", "registry:item": "item",
}

def human(name):
    return (name or "").replace("-", " ").replace("_", " ").strip()

def item_text(name, typ, desc):
    kind = TYPE_KIND.get(typ, "component")
    base = f"{human(name)} ({kind})"
    desc = (desc or "").strip()
    return f"{base}: {desc}" if desc else base

def enriched_text(it, registry):
    """Composite text for clustering: description + category + tags (post-enrichment)."""
    kind = it.get("kind") or TYPE_KIND.get(it.get("type", ""), "component")
    desc = (it.get("description") or "").strip()
    cat = (it.get("category") or "").replace("-", " ")
    tags = ", ".join(it.get("tags") or [])
    style = ", ".join(it.get("style") or [])
    uses = ", ".join(it.get("useCases") or [])
    parts = [f"{human(it.get('name',''))} ({kind})"]
    if desc: parts.append(desc)
    if cat: parts.append(f"Category: {cat}.")
    if tags: parts.append(f"Tags: {tags}.")
    if style: parts.append(f"Style: {style}.")
    if uses: parts.append(f"Use cases: {uses}.")
    return " ".join(parts)

def h(text):
    return hashlib.sha1(f"{MODEL}|{DIMS}|{text}".encode()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only first N items (testing)")
    ap.add_argument("--dry-run", action="store_true", help="no API calls; just report counts/cost")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    enr = json.load(open("data/registries.enriched.json"))
    items = []
    for r in enr["registries"]:
        c = r["components"]
        if not c["found"]:
            continue
        for it in c["items"]:
            nm = it.get("name")
            if not nm:
                continue
            items.append({
                "id": f'{r["handle"]}/{nm}',
                "handle": r["handle"],
                "registry": r["name"],
                "name": nm,
                "type": it.get("type", ""),
                "terminology": c.get("terminology"),
                "description": it.get("description", "") or "",
                "category": it.get("category", ""),
                "text": enriched_text(it, r),
            })
    if args.limit:
        items = items[:args.limit]

    # dedup by text
    uniq = {}
    for it in items:
        uniq.setdefault(it["text"], len(uniq))
    unique_texts = [None] * len(uniq)
    for t, i in uniq.items():
        unique_texts[i] = t
    for it in items:
        it["uidx"] = uniq[it["text"]]

    # rough token estimate (~1 token / 4 chars)
    est_tokens = sum(len(t) for t in unique_texts) / 4
    est_cost = est_tokens / 1e6 * PRICE
    print(f"items: {len(items):,} | unique texts: {len(unique_texts):,} "
          f"(dedup saves {100*(1-len(unique_texts)/max(1,len(items))):.0f}%)")
    print(f"model: {MODEL} ({DIMS}d) | est ~{est_tokens/1e3:.0f}k tokens | est cost ~${est_cost:.3f}")
    if args.dry_run:
        print("dry-run: no API calls made.")
        return

    # reuse cached vectors for unchanged texts
    cache = {}
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        cache = dict(zip(z["keys"].tolist(), z["vecs"]))
    vecs = np.zeros((len(unique_texts), DIMS), dtype=np.float16)
    todo = []
    for i, t in enumerate(unique_texts):
        v = cache.get(h(t))
        if v is not None:
            vecs[i] = v
        else:
            todo.append(i)
    print(f"cached: {len(unique_texts) - len(todo):,} | to embed: {len(todo):,}", flush=True)

    client = OpenAI()
    BATCH = 256
    t0 = time.time()
    total_tokens = 0
    lock = threading.Lock()
    def run(chunk_idx):
        nonlocal total_tokens
        chunk = [unique_texts[i] for i in chunk_idx]
        for attempt in range(8):
            try:
                resp = client.embeddings.create(model=MODEL, input=chunk, dimensions=DIMS)
                break
            except Exception as e:
                if attempt == 7:
                    raise
                print(f"  retry {attempt+1} after error: {str(e)[:80]}", file=sys.stderr)
                time.sleep(min(60, 2 ** attempt))
        with lock:
            for j, d in enumerate(resp.data):
                vecs[chunk_idx[j]] = np.asarray(d.embedding, dtype=np.float16)
            total_tokens += resp.usage.total_tokens
    chunks = [todo[s:s + BATCH] for s in range(0, len(todo), BATCH)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for k, _ in enumerate(ex.map(run, chunks), 1):
            if k % 20 == 0 or k == len(chunks):
                print(f"  {k}/{len(chunks)} batches ({time.time()-t0:.0f}s, {total_tokens/1e3:.0f}k tok)", flush=True)

    os.makedirs("data/embeddings", exist_ok=True)
    np.save("data/embeddings/unique_vectors.npy", vecs)
    np.savez(CACHE, keys=np.array([h(t) for t in unique_texts]), vecs=vecs)
    sv = vecs[:, :SEARCH_DIMS].astype(np.float32)
    sv /= np.linalg.norm(sv, axis=1, keepdims=True) + 1e-12
    np.save(f"data/embeddings/search_vectors_{SEARCH_DIMS}.npy", sv.astype(np.float16))
    json.dump(unique_texts, open("data/embeddings/unique_texts.json", "w"))
    json.dump(items, open("data/embeddings/items.json", "w"), ensure_ascii=False)
    json.dump({
        "model": MODEL, "dimensions": DIMS, "searchDimensions": SEARCH_DIMS,
        "items": len(items), "uniqueTexts": len(unique_texts), "embeddedThisRun": len(todo),
        "totalTokens": total_tokens, "actualCost": round(total_tokens / 1e6 * PRICE, 4),
        "builtAt": time.strftime("%Y-%m-%d"),
    }, open("data/embeddings/meta.json", "w"), indent=2)
    print(f"\nDONE: {len(unique_texts):,} vectors ({DIMS}d, search {SEARCH_DIMS}d) for {len(items):,} items in "
          f"{time.time()-t0:.0f}s | {total_tokens/1e3:.0f}k tokens | cost ${total_tokens/1e6*PRICE:.4f}")

if __name__ == "__main__":
    main()
