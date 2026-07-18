#!/usr/bin/env python3
"""
Prototype: discover exact per-component deep links for given registries.
Sources (ground-truth first): (1) sitemap URLs, (2) listing-page anchor hrefs,
(3) derived template + HTTP verify with soft-404 fingerprinting.
Usage: python scripts/deeplinks_probe.py @aceternity @cult-ui ...
"""
import sys, re, json, gzip, urllib.request, urllib.parse, concurrent.futures
from collections import Counter

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
enr = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}
pages = json.load(open("data/raw/pages.json"))

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(1_500_000)
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return r.geturl(), r.status, raw.decode("utf-8", "replace")

def domain(u):
    n = urllib.parse.urlparse(u).netloc
    return n[4:] if n.startswith("www.") else n

def sitemap_urls(home):
    host = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(home))
    urls, seen, todo = set(), set(), [host + p for p in
        ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-0.xml", "/sitemap/sitemap.xml"]]
    while todo and len(seen) < 15:
        sm = todo.pop()
        if sm in seen: continue
        seen.add(sm)
        try: _, _, body = fetch(sm, 12)
        except Exception: continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        if "<sitemapindex" in body:
            todo.extend(l for l in locs if l.endswith(".xml"))
        else:
            urls.update(locs)
    return urls

def listing_hrefs(urls, home_dom):
    hrefs = set()
    for u in urls:
        try: final, _, html = fetch(u, 12)
        except Exception: continue
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', html):
            absu = urllib.parse.urljoin(final, m.group(1))
            if absu.startswith("http") and domain(absu) == home_dom:
                hrefs.add(absu.split("?")[0].rstrip("/"))
    return hrefs

def last_seg(u):
    return urllib.parse.urlparse(u).path.rstrip("/").split("/")[-1]

def probe(handle):
    reg = enr[handle]; home = reg["homepage"]
    home_dom = domain(home)
    items = [it["name"] for it in reg["components"]["items"] if it.get("name")]
    itemset = set(items)
    # gather candidate URLs
    sm = sitemap_urls(home)
    listing = listing_hrefs([p["url"] for p in pages.get(handle, [])], home_dom)
    pool = sm | listing
    # index pool by last segment
    by_seg = {}
    for u in pool:
        by_seg.setdefault(last_seg(u), []).append(u)
    matched = {}
    for name in items:
        cands = by_seg.get(name)
        if cands:
            # prefer the shortest path (canonical), containing a component-ish segment
            cands.sort(key=lambda u: (len(urllib.parse.urlparse(u).path.split("/")), len(u)))
            matched[name] = cands[0]
    # derive dominant template from matched
    tmpl = None
    if matched:
        prefixes = Counter()
        for name, u in matched.items():
            p = urllib.parse.urlparse(u)
            path = p.path.rstrip("/")
            if path.endswith("/" + name):
                prefixes[(p.scheme + "://" + p.netloc, path[:-len(name)])] += 1
        if prefixes:
            (host, pre), _ = prefixes.most_common(1)[0]
            tmpl = host + pre + "{name}"
    return {
        "handle": handle, "items": len(items), "sitemap_urls": len(sm),
        "listing_hrefs": len(listing), "matched": len(matched),
        "coverage": round(100 * len(matched) / max(1, len(items))),
        "template": tmpl,
        "sample": dict(list(matched.items())[:3]),
    }

targets = sys.argv[1:] or ["@aceternity", "@cult-ui", "@magicui", "@neobrutalism", "@7ovr"]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for r in ex.map(probe, targets):
        print(f'\n{r["handle"]}  items={r["items"]} matched={r["matched"]} '
              f'({r["coverage"]}%)  sitemap={r["sitemap_urls"]} listing={r["listing_hrefs"]}')
        print(f'  template: {r["template"]}')
        for n, u in r["sample"].items():
            print(f'    {n} -> {u}')
