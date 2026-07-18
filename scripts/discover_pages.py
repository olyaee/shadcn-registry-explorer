#!/usr/bin/env python3
"""
Discover each registry's actual browse page(s) — the /components, /blocks, /elements,
/icons, ... listing you can click straight into. Up to 2 links per registry.

Method per registry:
  1) if the homepage URL already points at a browse page, keep it
  2) parse homepage HTML for internal nav links matching browse keywords
  3) probe a curated set of common browse paths
  Validate every candidate (HTTP 200, not a redirect back to the site root),
  classify by category, keep the best per category, return up to 2
  (prioritising the categories that match the registry's terminology).

Output: data/raw/pages.json  { "@handle": [ {"label","url"}, ... ] }
"""
import json, re, sys, urllib.request, urllib.error, urllib.parse, concurrent.futures
from collections import OrderedDict

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")

enr = json.load(open("data/registries.enriched.json"))
REGS = [r for r in enr["registries"] if r["components"]["found"]]
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else len(REGS)

CATS = [  # (category, label, regex on slug)
    ("blocks",     "Blocks",     re.compile(r"block", re.I)),
    ("components", "Components", re.compile(r"component", re.I)),
    ("elements",   "Elements",   re.compile(r"element", re.I)),
    ("icons",      "Icons",      re.compile(r"icon", re.I)),
    ("templates",  "Templates",  re.compile(r"template", re.I)),
    ("charts",     "Charts",     re.compile(r"chart", re.I)),
    ("fonts",      "Fonts",      re.compile(r"font", re.I)),
    ("primitives", "Primitives", re.compile(r"primitive", re.I)),
    ("ui",         "UI",         re.compile(r"/ui/?$", re.I)),
    ("docs",       "Docs",       re.compile(r"/docs/?$|/documentation/?$", re.I)),
]
EXCLUDE = re.compile(r"(mailto:|javascript:|tel:|/blog|/pricing|/login|/sign|/register|"
                     r"/changelog|/about|/contact|/terms|/privacy|/api/|\.json$|\.xml$|"
                     r"github\.com|twitter\.com|x\.com|discord|linkedin|/installation|"
                     r"/getting-started|/introduction)", re.I)
PROBE_PATHS = ["/components", "/docs/components", "/blocks", "/docs/blocks",
               "/elements", "/docs/elements", "/icons", "/templates", "/charts",
               "/ui", "/docs", "/primitives", "/all"]

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        final = r.geturl()
        body = r.read(400_000).decode("utf-8", "replace")
        return final, body

def head_ok(url, timeout=10):
    """Return final URL if 200 and not redirected to bare root, else None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = r.geturl()
            if r.status != 200:
                return None
            # reject redirect that collapses to site root
            if urllib.parse.urlparse(final).path.strip("/") == "":
                return None
            r.read(1024)
            return final
    except Exception:
        return None

CAT_KW = {"blocks": "block", "components": "component", "elements": "element",
          "icons": "icon", "templates": "template", "charts": "chart",
          "fonts": "font", "primitives": "primitive"}

def categorize(slug):
    for cat, label, rx in CATS:
        if rx.search(slug):
            return cat, label
    return None, None

def trim_to_root(url, cat):
    """Trim a deep link (/components/foo/bar) to its category listing root (/components)."""
    kw = CAT_KW.get(cat)
    if not kw:
        return url
    parts = urllib.parse.urlsplit(url)
    segs = [s for s in parts.path.split("/")]
    for i, s in enumerate(segs):
        if kw in s.lower():
            newpath = "/".join(segs[:i + 1])
            return urllib.parse.urlunsplit((parts.scheme, parts.netloc, newpath, "", ""))
    return url

def domain(u):
    n = urllib.parse.urlparse(u).netloc
    return n[4:] if n.startswith("www.") else n

def discover(reg):
    handle = reg["handle"]; home = reg["homepage"].rstrip("/")
    term = (reg["components"].get("terminology") or "").lower()
    home_dom = domain(home)
    cand = OrderedDict()   # url -> (cat, label)

    # 1) homepage itself already a browse page?
    hp_path = urllib.parse.urlparse(home).path
    c, l = categorize(hp_path)
    if c:
        cand[home] = (c, l)

    # 2) parse homepage nav links
    try:
        final, html = fetch(home + "/")
        for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
            href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
            if EXCLUDE.search(href):
                continue
            url = urllib.parse.urljoin(final + "/", href)
            if not url.startswith("http"):
                continue
            if domain(url) != home_dom:
                continue
            slug = urllib.parse.urlparse(url).path
            if slug.strip("/") == "":
                continue
            c, l = categorize(slug + " " + text)
            if c:
                root = trim_to_root(url, c)   # prefer the listing root over deep item links
                if root not in cand:
                    cand[root] = (c, l)
                if url not in cand:
                    cand[url] = (c, l)
    except Exception:
        pass

    # validate candidates from steps 1-2
    valid = OrderedDict()
    for url, (c, l) in cand.items():
        ok = head_ok(url)
        if ok:
            valid[ok] = (c, l)

    # 3) probe common paths only if we have <2 categories so far
    have_cats = {c for c, _ in valid.values()}
    if len(have_cats) < 2:
        for p in PROBE_PATHS:
            url = home + p
            if url in valid:
                continue
            c, l = categorize(p)
            if not c or c in have_cats:
                continue
            ok = head_ok(url)
            if ok:
                valid[ok] = (c, l)
                have_cats.add(c)
            if len(have_cats) >= 2:
                break

    # rank: categories matching the registry terminology first
    def score(item):
        url, (c, l) = item
        s = 0
        if c in term: s -= 5
        if l.lower() in term: s -= 5
        # shorter path = more likely the top-level gallery
        s += urllib.parse.urlparse(url).path.count("/")
        return s
    ranked = sorted(valid.items(), key=score)
    # dedupe by category, keep up to 2
    out, seen = [], set()
    for url, (c, l) in ranked:
        if c in seen:
            continue
        seen.add(c)
        out.append({"label": l, "url": url})
        if len(out) >= 2:
            break
    # fallback: nothing found -> keep homepage
    if not out:
        out = [{"label": "Home", "url": reg["homepage"]}]
    return handle, out

def main():
    results = {}
    regs = REGS[:LIMIT]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(discover, r) for r in regs]
        done = 0
        for f in concurrent.futures.as_completed(futs):
            h, links = f.result()
            results[h] = links
            done += 1
            if done % 25 == 0:
                print(f"  ...{done}/{len(regs)}", file=sys.stderr)
    # stable order by handle
    results = {k: results[k] for k in sorted(results, key=str.lower)}
    json.dump(results, open("data/raw/pages.json", "w"), indent=2, ensure_ascii=False)
    multi = sum(1 for v in results.values() if len(v) >= 2)
    home_only = sum(1 for v in results.values() if len(v) == 1 and v[0]["label"] == "Home")
    print(f"discovered pages for {len(results)} registries | {multi} have 2 links | "
          f"{home_only} fell back to homepage")

if __name__ == "__main__":
    main()
