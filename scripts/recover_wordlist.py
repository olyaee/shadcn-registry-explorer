#!/usr/bin/env python3
"""
Data-driven brute recovery: mine the most common item names from the 220 already
enumerated registries, then probe each unresolved registry's item template with
that wordlist. Recovers registries that use conventional item names but expose no
index/sitemap. Writes data/raw/recover/wordlist.json.
"""
import json, re, urllib.request, concurrent.futures
from collections import Counter
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")
STYLES = ["default","new-york","new-york-v4"]

enr = json.load(open("data/registries.enriched.json"))
name_counter = Counter()
for r in enr["registries"]:
    for it in r["components"]["items"]:
        if it.get("name"):
            name_counter[it["name"]] += 1

# wordlist: names appearing in >=2 registries, capped; plus curated shadcn base
BASE = """accordion alert alert-dialog aspect-ratio avatar badge breadcrumb button
button-group calendar card carousel chart checkbox collapsible combobox command
context-menu data-table date-picker dialog drawer dropdown-menu empty field form
hover-card input input-group input-otp item kbd label menubar navigation-menu
pagination popover progress radio-group resizable scroll-area select separator
sheet sidebar skeleton slider sonner spinner switch table tabs textarea toast
toggle toggle-group tooltip""".split()
mined = [n for n,c in name_counter.most_common() if c >= 2]
WORDLIST = list(dict.fromkeys(BASE + mined))[:600]
print(f"wordlist size: {len(WORDLIST)}")

self = json.load(open("data/raw/recover/self.json"))
UNRES = [r for r in self if r["status"] not in ("found","partial")]
TMPL = {e["handle"]: e["urlTemplate"] for e in json.load(open("data/raw/not_found_28.json"))}

def get_json(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8","replace"))

def slim(d):
    return {"name": d.get("name"), "type": d.get("type",""),
            "title": d.get("title","") or "", "description": d.get("description","") or ""}

def terminology(items):
    LABEL={"registry:block":"Blocks","registry:ui":"Components","registry:component":"Components",
           "registry:hook":"Hooks","registry:page":"Pages","registry:theme":"Themes",
           "registry:style":"Themes","registry:icon":"Icons","registry:lib":"Utilities"}
    types=[i["type"] for i in items if i.get("type")]
    return LABEL.get(Counter(types).most_common(1)[0][0],"Components") if types else "Items"

def recover(r):
    h=r["handle"]; tmpl=TMPL[h]
    styles = STYLES if "{style}" in tmpl else ["default"]
    # find live style using a tiny probe first
    def fetch(name, style):
        try:
            d=get_json(tmpl.replace("{name}",name).replace("{style}",style))
            if isinstance(d,dict) and str(d.get("type","")).startswith("registry:"):
                return slim(d)
        except Exception: return None
    live_style="default"
    if "{style}" in tmpl:
        for s in styles:
            if any(fetch(n,s) for n in ["button","card","accordion"]):
                live_style=s; break
    found={}
    def task(n):
        return fetch(n, live_style)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        for res in ex.map(task, WORDLIST):
            if res: found[res["name"]]=res
    out=dict(handle=h, homepage=r["homepage"], status="not_found", method="wordlist-brute",
             indexUrl=None, itemCount=0, items=[], terminology=r.get("terminology"), notes=r.get("notes",""))
    if found:
        items=sorted(found.values(), key=lambda x:x["name"])
        out.update(status="found" if len(items)>=5 else "partial",
                   itemCount=len(items), items=items, terminology=terminology(items))
    return out

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for r in ex.map(recover, UNRES):
        results.append(r)
        print(f'  {r["handle"]:<18} {r["status"]:<10} items={r["itemCount"]}')

json.dump(results, open("data/raw/recover/wordlist.json","w"), indent=2, ensure_ascii=False)
rec=[r for r in results if r["status"] in ("found","partial")]
print(f"\nwordlist recovered {len(rec)}/{len(results)}, {sum(r['itemCount'] for r in rec)} items")
