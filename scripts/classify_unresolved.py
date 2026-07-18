#!/usr/bin/env python3
"""
For registries we couldn't enumerate, do a light classification:
 - fetch homepage -> <title>, meta description, nav keyword scan (terminology)
 - probe the item template with a few common names to see if the registry is live
Outputs data/raw/recover/classify.json (schema compatible w/ build_enriched: adds
'terminology' + notes; leaves status not_found/dead/gated).
"""
import json, re, urllib.request, urllib.error, concurrent.futures
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")

self = json.load(open("data/raw/recover/self.json"))
UNRES = [r for r in self if r["status"] not in ("found", "partial")]
TMPL = {e["handle"]: e["urlTemplate"] for e in json.load(open("data/raw/not_found_28.json"))}

PROBE = ["button","card","badge","accordion","input","dialog","hero","hero-1",
         "navbar","footer","avatar","icon","alert","tabs","table"]
STYLES = ["default","new-york","new-york-v4"]
KW = ["component","block","element","icon","template","theme","font","primitive","pattern","section","widget","hook","chart","animation"]

def get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8","replace")

def classify(r):
    h = r["handle"]; home = r["homepage"]; tmpl = TMPL[h]
    out = dict(r)
    # homepage scan
    title=desc=""; kwcounts={}
    try:
        html = get(home)
        m=re.search(r"<title>(.*?)</title>", html, re.I|re.S); title=(m.group(1).strip() if m else "")[:120]
        m=re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.I); desc=(m.group(1) if m else "")[:200]
        low=html.lower()
        for k in KW:
            c=low.count(k)
            if c: kwcounts[k]=c
    except Exception as e:
        out["notes"]=(out.get("notes","")+f" homepage: {type(e).__name__}").strip()
    # terminology guess from keyword frequency (plural label)
    term=None
    if kwcounts:
        top=sorted(kwcounts.items(), key=lambda x:-x[1])[0][0]
        term={"component":"Components","block":"Blocks","element":"Elements","icon":"Icons",
              "template":"Templates","theme":"Themes","font":"Fonts","primitive":"Primitives",
              "pattern":"Patterns","section":"Sections","widget":"Widgets","hook":"Hooks",
              "chart":"Charts","animation":"Animations"}.get(top)
    out["terminology"]=out.get("terminology") or term
    out["siteTitle"]=title; out["siteDescription"]=desc
    # liveness probe
    live=[]
    styles = STYLES if "{style}" in tmpl else ["default"]
    def check(args):
        n,s=args; u=tmpl.replace("{name}",n).replace("{style}",s)
        try:
            d=json.loads(get(u,8))
            if isinstance(d,dict) and str(d.get("type","")).startswith("registry:"):
                return d.get("name")
        except Exception: return None
    tasks=[(n,s) for n in PROBE for s in styles]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for res in ex.map(check, tasks):
            if res: live.append(res)
    out["registryLive"]=bool(live)
    out["liveSample"]=sorted(set(live))
    return out

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(classify, UNRES):
        results.append(r)
        print(f'  {r["handle"]:<18} term={str(r.get("terminology")):<12} live={r.get("registryLive")} sample={r.get("liveSample")}')

json.dump(results, open("data/raw/recover/classify.json","w"), indent=2, ensure_ascii=False)
print("wrote data/raw/recover/classify.json")
