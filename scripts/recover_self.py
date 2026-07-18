#!/usr/bin/env python3
"""
Self-contained recovery for the 28 registries lacking a standard index.
Strategy per registry:
  A) try non-standard index JSON locations
  B) sitemap slug discovery -> validate each candidate name against the item template
Writes data/raw/recover/self.json in the agent schema so build_enriched.py picks it up.
"""
import json, re, sys, gzip, io, urllib.request, urllib.error, concurrent.futures, time
from collections import Counter

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
STYLES = ["default", "new-york", "new-york-v4", "new-york-v3"]

NF = json.load(open("data/raw/not_found_28.json"))

def get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = r.headers.get("Content-Encoding", "")
    if raw[:2] == b"\x1f\x8b" or "gzip" in enc:
        try: raw = gzip.decompress(raw)
        except Exception: pass
    return raw

def get_json(url, timeout=15):
    return json.loads(get(url, timeout).decode("utf-8", "replace"))

def host_of(u):
    m = re.match(r'(https?://[^/]+)', u); return m.group(1) if m else None

def item_url(tmpl, name, style="default"):
    return tmpl.replace("{name}", name).replace("{style}", style)

def valid_item(d):
    return isinstance(d, dict) and d.get("name") and str(d.get("type", "")).startswith("registry:")

def slim(d):
    return {"name": d.get("name"), "type": d.get("type", ""),
            "title": d.get("title", "") or "", "description": d.get("description", "") or ""}

def index_candidates(tmpl):
    cands = []
    c = tmpl.replace("{name}", "registry")
    c = re.sub(r"\{style\}", "default", c)
    cands.append(c)
    m = re.match(r'(https?://.*?/)[^/]*\{', tmpl)
    if m: cands.append(m.group(1) + "registry.json")
    h = host_of(tmpl)
    for p in ("/r/registry.json", "/registry.json", "/r/index.json", "/api/registry", "/registry"):
        cands.append(h + p)
    seen, out = set(), []
    for x in cands:
        if x not in seen: seen.add(x); out.append(x)
    return out

def try_index(tmpl):
    for cand in index_candidates(tmpl):
        try:
            d = get_json(cand, 12)
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("items"), list):
            items = [slim(it) for it in d["items"] if valid_item(it)]
            if items:
                return cand, items
    return None, None

SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-0.xml",
                 "/sitemap/sitemap-0.xml", "/sitemap-index.xml"]

def collect_sitemap_urls(host):
    urls = set()
    to_visit = [host + p for p in SITEMAP_PATHS]
    visited = set()
    while to_visit and len(visited) < 12:
        sm = to_visit.pop()
        if sm in visited: continue
        visited.add(sm)
        try:
            body = get(sm, 12).decode("utf-8", "replace")
        except Exception:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
        if "<sitemapindex" in body:
            to_visit.extend(l for l in locs if l.endswith(".xml"))
        else:
            urls.update(locs)
    return urls

COMPONENTISH = re.compile(r"/(components?|blocks?|elements?|icons?|ui|docs|r|registry|primitives?|charts?|templates?|hooks?)/", re.I)

def candidate_names(urls):
    names = set()
    for u in urls:
        path = re.sub(r"[?#].*$", "", u)
        segs = [s for s in path.split("/")[3:] if s]  # drop scheme+host
        if not segs: continue
        last = segs[-1]
        if last in ("", "docs", "components", "blocks", "index", "index.html"):
            pass
        # prefer component-ish urls, but keep all leaf slugs as fallback
        names.add(last)
        if len(segs) >= 2:
            names.add(segs[-2] + "/" + segs[-1])
    # clean
    return {re.sub(r"\.html?$", "", n) for n in names if n and len(n) < 60 and not n.endswith(".xml")}

def validate_names(tmpl, names, cap=260):
    has_style = "{style}" in tmpl
    styles = STYLES if has_style else ["default"]
    names = list(names)[:cap]
    found = {}
    # pick working style first (probe a few names across styles)
    chosen_styles = styles
    def check(args):
        name, style = args
        try:
            d = get_json(item_url(tmpl, name, style), 10)
        except Exception:
            return None
        if valid_item(d):
            return slim(d)
        return None
    # build task list: for style templates, try styles until one hits, then lock it
    tasks = []
    if has_style:
        # probe first ~8 names against each style to find the live style
        probe_names = names[:8]
        live_style = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            for style in styles:
                res = list(ex.map(check, [(n, style) for n in probe_names]))
                if any(res):
                    live_style = style
                    for n, r in zip(probe_names, res):
                        if r: found[r["name"]] = r
                    break
        if not live_style:
            return {}
        tasks = [(n, live_style) for n in names if n not in found]
    else:
        tasks = [(n, "default") for n in names]
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for r in ex.map(check, tasks):
            if r: found[r["name"]] = r
    return found

def terminology(items):
    types = [i.get("type", "") for i in items if i.get("type")]
    if not types: return "Items"
    LABEL = {"registry:block":"Blocks","registry:ui":"Components","registry:component":"Components",
             "registry:hook":"Hooks","registry:page":"Pages","registry:theme":"Themes",
             "registry:style":"Themes","registry:icon":"Icons","registry:lib":"Utilities"}
    return LABEL.get(Counter(types).most_common(1)[0][0], "Components")

def recover_one(entry):
    handle, home, tmpl = entry["handle"], entry["homepage"], entry["urlTemplate"]
    out = {"handle": handle, "homepage": home, "terminology": None,
           "status": "not_found", "method": None, "indexUrl": None,
           "itemCount": 0, "items": [], "notes": ""}
    host = host_of(tmpl)
    # A) index
    try:
        idx_url, items = try_index(tmpl)
    except Exception as e:
        idx_url, items = None, None
    if items:
        out.update(status="found", method="index", indexUrl=idx_url,
                   itemCount=len(items), items=items, terminology=terminology(items))
        return out
    # B) sitemap
    try:
        urls = collect_sitemap_urls(host)
    except Exception as e:
        urls = set()
        out["notes"] = f"sitemap error: {e}"
    if urls:
        comp_urls = [u for u in urls if COMPONENTISH.search(u)] or list(urls)
        names = candidate_names(comp_urls)
        try:
            found = validate_names(tmpl, names)
        except Exception as e:
            found = {}
            out["notes"] += f" validate error: {e}"
        if found:
            items = sorted(found.values(), key=lambda x: x["name"])
            out.update(status="found" if len(items) >= 5 else "partial",
                       method="sitemap-slugs", itemCount=len(items),
                       items=items, terminology=terminology(items),
                       notes=(out["notes"] + f" sitemap_urls={len(urls)}").strip())
            return out
        else:
            out["notes"] = (out["notes"] + f" sitemap_urls={len(urls)} but 0 validated").strip()
    else:
        # detect dead / gated
        try:
            get(host, 10)
        except urllib.error.HTTPError as e:
            out["status"] = "gated" if e.code in (401, 403) else "not_found"
            out["notes"] = f"HTTP {e.code} on homepage"
        except Exception as e:
            out["status"] = "dead"
            out["notes"] = f"{type(e).__name__}: {str(e)[:60]}"
    return out

def main():
    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(recover_one, e): e["handle"] for e in NF}
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            results.append(r)
            print(f"  {r['handle']:<18} {r['status']:<10} items={r['itemCount']:<4} {r['method'] or ''}", file=sys.stderr)
    results.sort(key=lambda r: r["handle"].lower())
    import os
    os.makedirs("data/raw/recover", exist_ok=True)
    json.dump(results, open("data/raw/recover/self.json", "w"), indent=2, ensure_ascii=False)
    rec = [r for r in results if r["status"] in ("found", "partial")]
    print(f"\nrecovered {len(rec)}/{len(results)} registries, "
          f"{sum(r['itemCount'] for r in rec)} items, in {time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
