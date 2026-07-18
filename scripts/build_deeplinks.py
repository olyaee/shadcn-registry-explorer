#!/usr/bin/env python3
"""
Find the EXACT per-component deep link for every item, verifying each one.

Per registry:
  1. Build a URL pool: sitemap(s) + browse-page hrefs + ONE level of deeper crawl
     (fetch the component-ish pages found so far, collect their hrefs too — catches
      non-obvious patterns like 7ovr's /preview/{name}).
  2. Match each item name -> a pool URL by last path segment (ground truth).
  3. For still-unmatched *real* items (skip -demo/-example companion files), try a set
     of candidate templates via HTTP and verify (200 AND, on soft-404 sites, the item
     name must appear in the page). Accept the first that verifies.
  4. Classify every item: has-link (verified) | companion (demo/example, expected none) |
     no-page (verified absent) .

Resumable: writes data/raw/deeplinks/<handle>.json per registry; rerun skips done.
Usage: python scripts/build_deeplinks.py [--only @h ...] [--workers N] [--force]
"""
import os, sys, re, json, gzip, time, argparse, urllib.request, urllib.parse, concurrent.futures
from collections import Counter, defaultdict

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
OUT = "data/raw/deeplinks"
enr = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}
pages = json.load(open("data/raw/pages.json"))

REAL_TYPES = {"registry:ui", "registry:component", "registry:block", "registry:page",
              "registry:icon", "registry:theme"}
DEMO_RX = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)
COMPONENTISH = re.compile(r"/(components?|blocks?|elements?|primitives?|categor|docs|ui|"
                          r"preview|view|examples?|charts?|icons?|templates?)(/|$)", re.I)
CAND_PATHS = ["/components/{n}", "/docs/components/{n}", "/docs/{n}", "/blocks/{n}",
              "/preview/{n}", "/block/{n}", "/component/{n}", "/ui/{n}", "/elements/{n}",
              "/view/{n}", "/docs/blocks/{n}", "/examples/{n}", "/{n}"]

def fetch(url, timeout=15, maxbytes=1_200_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(maxbytes)
        if raw[:2] == b"\x1f\x8b":
            try: raw = gzip.decompress(raw)
            except Exception: pass
        return r.geturl(), r.status, raw.decode("utf-8", "replace")

def domain(u):
    n = urllib.parse.urlparse(u).netloc
    return n[4:] if n.startswith("www.") else n

def human(name):
    return re.sub(r"[-_]+", " ", name or "").strip().lower()

def title_of(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip().lower() if m else ""

def norm(u):
    return u.split("#")[0].split("?")[0].rstrip("/")

def hrefs_in(html, base, home_dom):
    out = set()
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html):
        absu = urllib.parse.urljoin(base, m.group(1))
        if absu.startswith("http") and domain(absu) == home_dom:
            out.add(norm(absu))
    return out

def sitemap_urls(home):
    host = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(home))
    urls, seen, todo = set(), set(), [host + p for p in
        ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-0.xml", "/sitemap/sitemap.xml", "/sitemap-index.xml"]]
    while todo and len(seen) < 25:
        sm = todo.pop()
        if sm in seen: continue
        seen.add(sm)
        try: _, _, body = fetch(sm, 12)
        except Exception: continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        if "<sitemapindex" in body:
            todo.extend(l for l in locs if l.endswith(".xml"))
        else:
            urls.update(norm(u) for u in locs)
    return urls

def last_seg(u):
    return urllib.parse.urlparse(u).path.rstrip("/").split("/")[-1]

def split_tmpl(u, name):
    p = urllib.parse.urlparse(u)
    path = p.path.rstrip("/")
    if path.endswith("/" + name):
        return (p.scheme + "://" + p.netloc, path[:-len(name)])
    return None

class Verifier:
    def __init__(self):
        self.fp = {}
    def fingerprint(self, host, prefix):
        key = (host, prefix)
        if key not in self.fp:
            try:
                _, st, html = fetch(host + prefix + "zzqbogus-xyz-42", 12)
                self.fp[key] = (st, len(html), title_of(html))
            except Exception as e:
                self.fp[key] = (getattr(e, "code", 404), -1, "")
        return self.fp[key]
    def verify(self, host, prefix, name, strict_name=True):
        url = host + prefix + name
        try:
            final, st, html = fetch(url, 12)
        except Exception:
            return None
        if st != 200:
            return None
        bst, blen, btitle = self.fingerprint(host, prefix)
        t = title_of(html); hn = human(name)
        name_present = (hn and hn in t) or (hn and hn in html[:6000].lower()) or (name.lower() in final.lower())
        if bst == 200:  # soft-404 site
            differs = abs(len(html) - blen) > 80 or (t and t != btitle)
            if strict_name and not name_present:
                return None
            if not (differs or name_present):
                return None
        return final

def build_pool(home, home_dom, seed_urls, crawl_cap=90):
    pool = set(seed_urls)
    # deepen: fetch component-ish pages from the seed, collect their hrefs
    to_crawl = [u for u in seed_urls if COMPONENTISH.search(u)][:crawl_cap]
    # always include the explicit browse pages
    fetched = 0
    for u in to_crawl:
        if fetched >= crawl_cap: break
        try:
            final, _, html = fetch(u, 12)
        except Exception:
            continue
        fetched += 1
        pool |= hrefs_in(html, final, home_dom)
    return pool

def process(handle):
    reg = enr[handle]; home = reg["homepage"]; home_dom = domain(home)
    host = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(home))
    items = [{"name": it["name"], "type": it.get("type", "")}
             for it in reg["components"]["items"] if it.get("name")]

    sm = sitemap_urls(home)
    browse = set()
    for p in pages.get(handle, []):
        try:
            final, _, html = fetch(p["url"], 12)
            browse.add(norm(final))
            browse |= hrefs_in(html, final, home_dom)
        except Exception:
            pass
    pool = build_pool(home, home_dom, sm | browse)
    by_seg = defaultdict(list)
    for u in pool:
        by_seg[last_seg(u)].append(u)

    links = {}
    for it in items:
        links[it["name"]] = {"url": None, "verified": False, "method": "none", "type": it["type"]}
    # ground-truth matches
    for it in items:
        name = it["name"]
        cands = by_seg.get(name)
        if cands:
            cands.sort(key=lambda u: (len(urllib.parse.urlparse(u).path.split("/")), len(u)))
            links[name] = {"url": cands[0], "verified": True,
                           "method": "sitemap" if cands[0] in sm else "crawl", "type": it["type"]}
    # derive dominant templates (per type + overall) from matches
    per_type = defaultdict(Counter); overall = Counter()
    for it in items:
        r = links[it["name"]]
        if r["url"]:
            sp = split_tmpl(r["url"], it["name"])
            if sp:
                per_type[it["type"]][sp] += 1; overall[sp] += 1
    dom_type = {t: c.most_common(1)[0][0] for t, c in per_type.items()}
    dom_all = overall.most_common(1)[0][0] if overall else None

    # candidate hosts: homepage + browse-page hosts + hosts of matched links
    cand_hosts = []
    def add_host(u):
        p = urllib.parse.urlparse(u)
        h = p.scheme + "://" + p.netloc
        if h not in cand_hosts:
            cand_hosts.append(h)
    for v in links.values():
        if v["url"]: add_host(v["url"])          # matched-link hosts first (most reliable)
    for p in pages.get(handle, []): add_host(p["url"])
    add_host(home)

    ver = Verifier()
    for it in items:
        name = it["name"]
        if links[name]["url"]:
            continue
        if DEMO_RX.search(name) or it["type"] == "registry:example":
            links[name]["method"] = "companion"          # demo/example: expected no page
            continue
        # candidate templates: dominant first, then standard set across candidate hosts
        cands = []
        for sp in [dom_type.get(it["type"]), dom_all]:
            if sp: cands.append(sp)
        for h in cand_hosts:
            for cp in CAND_PATHS:
                cands.append((h, cp[:-len("{n}")]))
        seen = set(); ok = None
        for hostp, pre in cands:
            if (hostp, pre) in seen: continue
            seen.add((hostp, pre))
            got = ver.verify(hostp, pre, name)
            if got:
                ok = got; break
        if ok:
            links[name] = {"url": ok, "verified": True, "method": "template", "type": it["type"]}
        else:
            links[name]["method"] = "no-page"            # verified: no dedicated page

    real = [it["name"] for it in items if it["type"] in REAL_TYPES and not DEMO_RX.search(it["name"])]
    real_linked = [n for n in real if links[n]["url"]]
    linked_total = sum(1 for v in links.values() if v["url"])
    method_counts = Counter(v["method"] for v in links.values())
    out = {
        "handle": handle, "homepage": home,
        "items": len(items), "linked": linked_total,
        "realItems": len(real), "realLinked": len(real_linked),
        "realCoverage": round(100 * len(real_linked) / max(1, len(real))),
        "templateStr": (dom_all[0] + dom_all[1] + "{name}") if dom_all else None,
        "methodCounts": dict(method_counts),
        "poolSize": len(pool),
        "links": links,
    }
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(f"{OUT}/{handle.lstrip('@')}.json", "w"), ensure_ascii=False)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    handles = args.only or [h for h in enr if enr[h]["components"]["found"]]
    if not args.force:
        handles = [h for h in handles if not os.path.exists(f"{OUT}/{h.lstrip('@')}.json")]
    print(f"processing {len(handles)} registries, {args.workers} workers", flush=True)
    t0 = time.time(); done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process, h): h for h in handles}
        for fut in concurrent.futures.as_completed(futs):
            h = futs[fut]
            try:
                r = fut.result(); done += 1
                print(f"  [{done}/{len(handles)}] {h:<22} real {r['realLinked']}/{r['realItems']} "
                      f"({r['realCoverage']}%)  total-linked={r['linked']}  {r['methodCounts']}", flush=True)
            except Exception as e:
                print(f"  ! {h}: {type(e).__name__}: {str(e)[:90]}", flush=True)
    print(f"done in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
