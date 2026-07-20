#!/usr/bin/env python3
"""
Data-quality pass 1: validate every registry browse link (and homepage).
Detects: dead/non-200, redirect-to-home (deep path lost), soft-404 (SPA returns
200 but shows a not-found page), and category keyword loss.
Writes data/quality/link_check.json + prints a summary.
"""
import json, re, os, urllib.request, urllib.parse, concurrent.futures, time
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")

pages = json.load(open("data/raw/pages.json"))
enr = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}

CATKW = re.compile(r"(component|block|element|icon|template|chart|font|primitive|hook)", re.I)
SOFT404 = re.compile(r"(404|not[\s-]*found|page (?:you|does).{0,20}(?:not|n't) exist|"
                     r"doesn't exist|no such page|page unavailable)", re.I)

def check(url):
    out = {"url": url, "status": None, "finalUrl": None, "redirectHome": False,
           "soft404": False, "keywordKept": None, "ok": False, "err": None}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=15) as r:
            out["status"] = r.status
            out["finalUrl"] = r.geturl()
            body = r.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code; out["err"] = f"HTTP {e.code}"; return out
    except Exception as e:
        out["err"] = f"{type(e).__name__}: {str(e)[:60]}"; return out

    fpath = urllib.parse.urlparse(out["finalUrl"]).path
    opath = urllib.parse.urlparse(url).path
    out["redirectHome"] = fpath.strip("/") == "" and opath.strip("/") != ""
    # soft-404: check <title> + first part of body
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    if m: title = m.group(1)
    head = (title + " " + body[:1500])
    out["soft404"] = bool(SOFT404.search(title)) or bool(SOFT404.search(head) and len(body) < 4000)
    if CATKW.search(opath):
        out["keywordKept"] = bool(CATKW.search(fpath))
    out["ok"] = (out["status"] == 200 and not out["redirectHome"] and not out["soft404"])
    return out

def main():
    tasks = []
    for handle, links in pages.items():
        for l in links:
            tasks.append((handle, l["label"], l["url"]))
    print(f"checking {len(tasks)} browse links across {len(pages)} registries...")
    results = {}
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        futmap = {ex.submit(check, url): (h, lbl, url) for h, lbl, url in tasks}
        done = 0
        for fut in concurrent.futures.as_completed(futmap):
            h, lbl, url = futmap[fut]
            results.setdefault(h, []).append({"label": lbl, **fut.result()})
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(tasks)} ({time.time()-t0:.0f}s)")

    os.makedirs("data/quality", exist_ok=True)
    json.dump(results, open("data/quality/link_check.json", "w"), ensure_ascii=False, indent=1)

    flat = [r for rs in results.values() for r in rs]
    ok = sum(1 for r in flat if r["ok"])
    dead = [r for r in flat if r["status"] is None or (r["status"] and r["status"] >= 400)]
    home = [r for r in flat if r["redirectHome"]]
    soft = [r for r in flat if r["soft404"]]
    kwlost = [r for r in flat if r["keywordKept"] is False and r["ok"]]
    # registries where ALL links are bad
    fully_bad = [h for h, rs in results.items() if not any(r["ok"] for r in rs)]
    print(f"\n=== {len(flat)} links checked in {time.time()-t0:.0f}s ===")
    print(f"  OK (200, not home, not soft-404): {ok}")
    print(f"  dead / >=400 status            : {len(dead)}")
    print(f"  redirect-to-home (path lost)   : {len(home)}")
    print(f"  soft-404 (SPA not-found)       : {len(soft)}")
    print(f"  category keyword lost on redirect: {len(kwlost)}")
    print(f"  registries with NO working link: {len(fully_bad)} -> {fully_bad}")

if __name__ == "__main__":
    main()
