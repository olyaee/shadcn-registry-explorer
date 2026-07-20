#!/usr/bin/env python3
"""
Embed every registry item with OpenAI text-embedding-3-large.

- Input : data/registries.enriched.json  (items with name/type/description)
- Text  : "<human name> (<kind>): <description>"  per item
- Dedup : identical texts embedded once, reused (many items are just "button", etc.)
- Output: data/embeddings/{unique_vectors.npy, unique_texts.json, items.json, meta.json}

Usage:  python scripts/embed_items.py [--limit N] [--dry-run]
"""
import os, json, sys, time, argparse
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
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
    parts = [f"{human(it.get('name',''))} ({kind})"]
    if desc: parts.append(desc)
    if cat: parts.append(f"Category: {cat}.")
    if tags: parts.append(f"Tags: {tags}.")
    return " ".join(parts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only first N items (testing)")
    ap.add_argument("--dry-run", action="store_true", help="no API calls; just report counts/cost")
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

    client = OpenAI()
    vecs = np.zeros((len(unique_texts), DIMS), dtype=np.float32)
    BATCH = 256
    t0 = time.time()
    total_tokens = 0
    for s in range(0, len(unique_texts), BATCH):
        chunk = unique_texts[s:s + BATCH]
        for attempt in range(4):
            try:
                resp = client.embeddings.create(model=MODEL, input=chunk, dimensions=DIMS)
                break
            except Exception as e:
                if attempt == 3:
                    raise
                print(f"  retry {attempt+1} after error: {str(e)[:80]}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        for j, d in enumerate(resp.data):
            vecs[s + j] = d.embedding
        total_tokens += resp.usage.total_tokens
        print(f"  {min(s+BATCH,len(unique_texts))}/{len(unique_texts)}  "
              f"({time.time()-t0:.0f}s, {total_tokens/1e3:.0f}k tok)", file=sys.stderr)

    os.makedirs("data/embeddings", exist_ok=True)
    np.save("data/embeddings/unique_vectors.npy", vecs)
    json.dump(unique_texts, open("data/embeddings/unique_texts.json", "w"))
    json.dump(items, open("data/embeddings/items.json", "w"), ensure_ascii=False)
    json.dump({
        "model": MODEL, "dimensions": DIMS, "items": len(items),
        "uniqueTexts": len(unique_texts), "totalTokens": total_tokens,
        "actualCost": round(total_tokens / 1e6 * PRICE, 4),
    }, open("data/embeddings/meta.json", "w"), indent=2)
    print(f"\nDONE: {len(unique_texts):,} vectors ({DIMS}d) for {len(items):,} items in "
          f"{time.time()-t0:.0f}s | {total_tokens/1e3:.0f}k tokens | "
          f"cost ${total_tokens/1e6*PRICE:.4f}")

if __name__ == "__main__":
    main()
