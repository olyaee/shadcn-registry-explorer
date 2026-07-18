#!/usr/bin/env python3
"""Fix @motion-primitives (agent left it incomplete; site rate-limits 429). Polite, spaced."""
import json, urllib.request, re, time
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
inp=json.load(open("data/raw/lowcov/motion-primitives.json"))
items=inp["items"]

def get(u):
    for a in range(6):
        try:
            req=urllib.request.Request(u,headers={"User-Agent":UA})
            with urllib.request.urlopen(req,timeout=15) as r:
                return r.status, r.read(120000).decode("utf-8","replace")
        except urllib.error.HTTPError as e:
            if e.code==429:
                time.sleep(5*(a+1)); continue
            return e.code, ""
        except Exception:
            time.sleep(2); continue
    return 429, ""

# calibrate 404 with a bogus name
_,_ = get("https://motion-primitives.com/docs/zzbogus-xyz")
time.sleep(1.5)

links={}
for it in items:
    n=it["name"]; typ=it.get("type","")
    url=None; method="no-page"
    for cand in [f"https://motion-primitives.com/docs/{n}"]:
        st,html=get(cand)
        if st==200 and (n.replace("-"," ").lower() in html.lower() or n.lower() in html.lower()):
            url=cand; method="url"; break
        time.sleep(1.2)
    links[n]={"url":url,"method":method,"type":typ}
    print(f"  {n:<28} {st} -> {method}")
    time.sleep(1.2)

json.dump({"handle":"@motion-primitives","homepage":inp["homepage"],"links":links},
          open("data/raw/deeplinks/motion-primitives.json","w"), ensure_ascii=False)
linked=sum(1 for v in links.values() if v["url"])
print(f"\nmotion-primitives: {linked}/{len(items)} linked")
