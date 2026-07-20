#!/usr/bin/env python3
"""
Verify EVERY generated per-item URL individually; keep only those that return 200,
are not soft-404, and whose page actually mentions the item. Guarantees the item
'view' links we ship are real. Writes data/quality/item_urls_verified.json.
"""
import json, re, urllib.request, concurrent.futures, time, os
from collections import Counter
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")}
SOFT404 = re.compile(r"(404|not[\s-]*found|page (?:does|doesn't).{0,20}exist)", re.I)

item_urls = json.load(open("data/quality/item_urls.json"))
items = {json.loads(l)["id"]: json.loads(l) for l in open("data/graph/items.jsonl")}

def variants(name):
    n = name.lower(); return {n, n.replace("-", " "), n.replace("-", ""), n.replace("_", " ")}

def verify(pair):
    iid, url = pair
    name = items[iid]["name"]
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10)
        if r.status != 200:
            return iid, None
        body = r.read(120_000).decode("utf-8", "replace")
    except Exception:
        return iid, None
    if SOFT404.search(body[:2000]):
        return iid, None
    low = body.lower()
    if any(v and v in low for v in variants(name)):
        return iid, url
    return iid, None

def main():
    pairs = list(item_urls.items())
    print(f"verifying {len(pairs)} per-item URLs individually...")
    kept = {}
    t0 = time.time(); done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        for iid, url in ex.map(verify, pairs):
            done += 1
            if url:
                kept[iid] = url
            if done % 1000 == 0:
                print(f"  {done}/{len(pairs)} ({time.time()-t0:.0f}s) kept={len(kept)}")
    json.dump(kept, open("data/quality/item_urls_verified.json", "w"))
    by_reg = Counter(items[i]["handle"] for i in kept)
    print(f"\n=== verified per-item URLs ===")
    print(f"  kept {len(kept)}/{len(pairs)} ({100*len(kept)/len(pairs):.0f}% survived) "
          f"in {time.time()-t0:.0f}s")
    print(f"  registries covered: {len(by_reg)}")
    print(f"  items with a verified view URL: {len(kept)} "
          f"({100*len(kept)/len(items):.0f}% of all {len(items)} items)")

if __name__ == "__main__":
    main()
