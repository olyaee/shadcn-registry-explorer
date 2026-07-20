#!/usr/bin/env python3
"""
Data-quality enrichment: discover a per-registry item-page URL pattern and build an
exact "view this component" URL for every item where it validates.

Per registry: try candidate URL templates on ~6 sample items; a template is accepted
only if >=60% of samples return HTTP 200, are NOT soft-404, AND the page actually
mentions the item name (guards against SPA catch-all 200s). The winning template is
then applied to ALL that registry's items (no per-item fetch).

Output: data/quality/item_urls.json  { "<item id>": "<url>" }  + a coverage report.
"""
import json, re, os, urllib.request, urllib.parse, concurrent.futures, time
from collections import defaultdict

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
SOFT404 = re.compile(r"(404|not[\s-]*found|page (?:does|doesn't).{0,20}exist|no such page)", re.I)

pages = json.load(open("data/raw/pages.json"))
enr = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}
items = [json.loads(l) for l in open("data/graph/items.jsonl")]
items_by_reg = defaultdict(list)
for it in items:
    items_by_reg[it["handle"]].append(it)

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.read(120_000).decode("utf-8", "replace")

def name_variants(name):
    n = name.lower()
    return {n, n.replace("-", " "), n.replace("-", ""), n.replace("_", " ")}

def page_has_item(body, name):
    low = body.lower()
    return any(v and v in low for v in name_variants(name))

def templates(handle):
    """Ordered candidate URL templates ({} = item name slot)."""
    home = enr[handle]["homepage"].rstrip("/")
    pl = pages.get(handle, [])
    browse = pl[0]["url"].rstrip("/") if pl else home
    cands = [browse + "/{}",
             home + "/docs/components/{}", home + "/components/{}",
             home + "/docs/{}", home + "/blocks/{}"]
    # second browse link (e.g. Blocks page) as a base too
    if len(pl) > 1:
        cands.insert(1, pl[1]["url"].rstrip("/") + "/{}")
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out

def detect(handle):
    its = items_by_reg.get(handle, [])
    if not its:
        return handle, None, 0
    # sample: prefer short, wordy names (skip pure numbers)
    sample = [it for it in its if not it["name"].isdigit()][:8]
    sample = sample[:6] if len(sample) >= 6 else sample
    for tmpl in templates(handle):
        hits = 0; tested = 0
        for it in sample:
            url = tmpl.format(urllib.parse.quote(it["name"], safe=""))
            tested += 1
            try:
                st, final, body = fetch(url)
            except Exception:
                continue
            if st == 200 and not SOFT404.search(body[:2000]) and page_has_item(body, it["name"]):
                hits += 1
        if tested and hits / tested >= 0.6:
            return handle, tmpl, hits / tested
    return handle, None, 0

def main():
    handles = [h for h in items_by_reg if h in enr]
    print(f"detecting item-URL patterns for {len(handles)} registries...")
    winners = {}
    t0 = time.time(); done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for handle, tmpl, conf in ex.map(detect, handles):
            done += 1
            if tmpl:
                winners[handle] = tmpl
            if done % 30 == 0:
                print(f"  {done}/{len(handles)} ({time.time()-t0:.0f}s) matched={len(winners)}")

    item_urls = {}
    for handle, tmpl in winners.items():
        for it in items_by_reg[handle]:
            item_urls[it["id"]] = tmpl.format(urllib.parse.quote(it["name"], safe=""))

    os.makedirs("data/quality", exist_ok=True)
    json.dump(item_urls, open("data/quality/item_urls.json", "w"))
    json.dump(winners, open("data/quality/item_url_templates.json", "w"), indent=1)
    reg_cov = len(winners); item_cov = len(item_urls)
    print(f"\n=== per-item URL enrichment ===")
    print(f"  registries with a working item-URL pattern: {reg_cov}/{len(handles)}")
    print(f"  items given an exact view URL: {item_cov}/{len(items)} "
          f"({100*item_cov/len(items):.0f}%)")
    print("  sample templates:")
    for h, t in list(winners.items())[:10]:
        print(f"    {h:<20} {t}")

if __name__ == "__main__":
    main()
