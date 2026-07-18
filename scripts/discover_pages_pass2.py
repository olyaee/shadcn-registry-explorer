#!/usr/bin/env python3
"""Targeted second pass for the registries that fell back to homepage.
Expanded path probing; if still nothing, relabel the homepage by the registry's
terminology (these are single-page galleries where the homepage IS the browse page)."""
import json, re, urllib.request, urllib.parse, concurrent.futures

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
pages = json.load(open("data/raw/pages.json"))
enr = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}
targets = [h for h, v in pages.items() if len(v) == 1 and v[0]["label"] == "Home"]

EXPANDED = ["/docs/components", "/components", "/docs", "/blocks", "/icons", "/charts",
            "/gallery", "/all", "/elements", "/primitives", "/hooks", "/ui", "/examples",
            "/docs/introduction", "/showcase"]
CATLABEL = [("block","Blocks"),("component","Components"),("element","Elements"),
            ("icon","Icons"),("chart","Charts"),("hook","Hooks"),("primitive","Primitives"),
            ("ui","UI"),("gallery","Gallery"),("example","Examples"),("docs","Docs")]

def label_for_path(p):
    for kw,l in CATLABEL:
        if kw in p.lower():
            return l
    return "Browse"

def ok(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = r.geturl()
            if r.status != 200: return None
            if urllib.parse.urlparse(final).path.strip("/") == "": return None
            r.read(1024); return final
    except Exception:
        return None

def fix(handle):
    reg = enr[handle]; home = reg["homepage"].rstrip("/")
    term = (reg["components"].get("terminology") or "").lower()
    found = []
    seen = set()
    for p in EXPANDED:
        u = ok(home + p)
        if u:
            lbl = label_for_path(p)
            key = lbl
            if key in seen: continue
            seen.add(key); found.append({"label": lbl, "url": u})
        if len(found) >= 2: break
    if found:
        # prioritise term match
        found.sort(key=lambda x: 0 if x["label"].lower() in term else 1)
        return handle, found[:2]
    # gallery fallback: relabel homepage by terminology
    lbl = {"components":"Components","blocks":"Blocks","icons":"Icons","themes":"Themes",
           "fonts":"Fonts","hooks":"Hooks","pages":"Pages","utilities":"Utilities"}.get(
               term.split(" ")[0] if term else "", "Gallery")
    return handle, [{"label": lbl, "url": reg["homepage"]}]

updated = 0; real = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
    for handle, links in ex.map(fix, targets):
        pages[handle] = links
        updated += 1
        if not (len(links) == 1 and links[0]["url"].rstrip("/") == enr[handle]["homepage"].rstrip("/")):
            real += 1
        print(f'  {handle:<22} ' + ' · '.join(f'[{l["label"]}] {l["url"]}' for l in links))

json.dump(pages, open("data/raw/pages.json", "w"), indent=2, ensure_ascii=False)
print(f"\nreprocessed {updated} | found a real sub-page for {real} | rest relabelled as gallery")
