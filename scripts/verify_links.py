#!/usr/bin/env python3
"""
Final verification: HTTP-check every assigned deep link actually returns 200.
'template' and 'no-page' were already HTTP-verified during discovery; this confirms
the 'sitemap' and 'crawl' links too. Broken links are nulled and marked 'broken'.
Updates each data/raw/deeplinks/<handle>.json in place. Resumable via a marker.
"""
import os, json, glob, urllib.request, urllib.parse, concurrent.futures, time
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")

def ok(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(2048)
            return r.status == 200
    except Exception:
        return False

def verify_registry(fp):
    d = json.load(open(fp))
    if d.get("verified_pass"):
        return d["handle"], 0, 0
    to_check = [(n, v["url"]) for n, v in d["links"].items()
                if v.get("url") and v.get("method") in ("sitemap", "crawl")]
    broken = 0
    # limit concurrency per-registry to be polite to the domain
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda t: (t[0], ok(t[1])), to_check))
    for name, good in results:
        if not good:
            d["links"][name]["url"] = None
            d["links"][name]["method"] = "broken"
            broken += 1
    # recompute simple counts
    REAL = {"registry:ui","registry:component","registry:block","registry:page","registry:icon","registry:theme"}
    import re
    DEMO = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)
    real = [n for n, v in d["links"].items() if v.get("type") in REAL and not DEMO.search(n)]
    real_linked = [n for n in real if d["links"][n]["url"]]
    d["realItems"] = len(real); d["realLinked"] = len(real_linked)
    d["realCoverage"] = round(100 * len(real_linked) / max(1, len(real)))
    d["linked"] = sum(1 for v in d["links"].values() if v["url"])
    from collections import Counter
    d["methodCounts"] = dict(Counter(v["method"] for v in d["links"].values()))
    d["verified_pass"] = True
    json.dump(d, open(fp, "w"), ensure_ascii=False)
    return d["handle"], len(to_check), broken

def main():
    files = sorted(glob.glob("data/raw/deeplinks/*.json"))
    print(f"verifying links across {len(files)} registries", flush=True)
    t0 = time.time(); tot_checked = tot_broken = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        for handle, checked, broken in ex.map(verify_registry, files):
            tot_checked += checked; tot_broken += broken
            if broken:
                print(f"  {handle}: {broken}/{checked} broken", flush=True)
    print(f"done in {time.time()-t0:.0f}s | checked {tot_checked} | broken {tot_broken}", flush=True)

if __name__ == "__main__":
    main()
