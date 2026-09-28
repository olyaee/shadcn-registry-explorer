#!/usr/bin/env python3
"""
Deep links for items added by the MCP refresh (`linkMethod: "pending"` in
registries.enriched.json). Existing links are never touched.

Per registry with pending items (reuses scripts/build_deeplinks.py helpers):
  1. URL pool = sitemap(s) + browse pages (data/raw/pages.json, else the homepage)
     + one level of crawl. Pending names are matched to pool URLs by last path segment.
  2. Templates are learned from links the registry ALREADY has (split on the item name)
     plus step-1 matches; the rest are verified against those templates over HTTP.
     A bounded full scan of standard paths (CAND_PATHS) runs for the first few
     unmatched items only, and templates that keep failing are dropped — so huge
     icon sets don't cost one probe per path per item.
     Slashed variant names (`fill/x`) take their base item's page ("variant-page").
  3. demo/example items -> "companion"; numbered series (`chart7`) inherit a shared page
     that >=80% of same-stem siblings already use; if >=80% of the registry's existing linked
     items of that type share ONE page (icon galleries etc.), unlinked real items get
     that page as "shared-page"; everything else -> "no-page".

Output: data/raw/deeplinks_pending/<handle>.json   (resumable; --force to redo)
Then:   python scripts/deeplinks_pending.py --merge   (fills pending items + link stats)
Usage:  python scripts/deeplinks_pending.py [--only @a @b] [--workers 10] [--force] [--merge]
"""
import os, re, sys, json, time, argparse, threading, urllib.parse, concurrent.futures
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
import build_deeplinks as bd                       # fetch / sitemap / crawl / verifier helpers
from update_from_mcp import link_stats

ENR = "data/registries.enriched.json"
OUT = "data/raw/deeplinks_pending"
FULL_SCAN_BUDGET = 6      # unmatched items that get the full CAND_PATHS scan
DROP_AFTER = 15           # drop a template after this many misses with zero hits

def pending_of(reg):
    return [i for i in reg["components"]["items"] if i.get("linkMethod") == "pending"]

def process(reg):
    handle, home = reg["handle"], reg["homepage"]
    home_dom = bd.domain(home)
    items = reg["components"]["items"]
    pend = pending_of(reg)
    links = {i["name"]: {"url": None, "method": "none"} for i in pend}

    # 1. ground-truth pool
    sm = bd.sitemap_urls(home)
    browse = set()
    for p in bd.pages.get(handle) or [{"url": home}]:
        try:
            final, _, html = bd.fetch(p["url"], 12)
            browse.add(bd.norm(final))
            browse |= bd.hrefs_in(html, final, home_dom)
        except Exception:
            pass
    pool = bd.build_pool(home, home_dom, sm | browse, crawl_cap=60)
    by_seg = defaultdict(list)
    for u in pool:
        by_seg[bd.last_seg(u)].append(u)
    for it in pend:
        segs = it["name"].split("/")
        c = by_seg.get(segs[-1])
        if c and len(segs) > 1:
            c = [u for u in c if all(sg in urllib.parse.urlparse(u).path.split("/") for sg in segs[:-1])]
        if c:
            c.sort(key=lambda u: (len(urllib.parse.urlparse(u).path.split("/")), len(u)))
            links[it["name"]] = {"url": c[0], "method": "sitemap" if c[0] in sm else "crawl"}

    # 2. templates from existing + matched links
    per_type, overall = defaultdict(Counter), Counter()
    shared = defaultdict(Counter)
    for it in items:
        u = it.get("url") if it.get("linkMethod") != "pending" else links.get(it["name"], {}).get("url")
        if not u:
            continue
        shared[it.get("type", "")][u] += 1
        sp = bd.split_tmpl(u, it["name"])
        if sp:
            per_type[it.get("type", "")][sp] += 1
            overall[sp] += 1
    tmpl_stats = defaultdict(lambda: [0, 0])      # sp -> [hits, misses]
    lock = threading.Lock()
    learned = [sp for sp, _ in overall.most_common(4)]
    ver = bd.Verifier()

    def templates_for(t):
        order = [sp for sp, _ in per_type[t].most_common(2)] + learned
        seen, out = set(), []
        for sp in order:
            s = tmpl_stats[sp]
            if sp in seen or (s[0] == 0 and s[1] >= DROP_AFTER):
                continue
            seen.add(sp); out.append(sp)
        return out

    def try_item(it, full_scan):
        name, t = it["name"], it.get("type", "")
        cands = templates_for(t)
        if full_scan:
            hosts = []
            for sp in cands:
                hosts.append(sp[0])
            for p in bd.pages.get(handle) or []:
                hosts.append("{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(p["url"])))
            hosts.append("{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(home)))
            for h in dict.fromkeys(hosts):
                cands += [(h, cp[:-len("{n}")]) for cp in bd.CAND_PATHS]
        for sp in dict.fromkeys(cands):
            got = ver.verify(sp[0], sp[1], name)
            with lock:
                tmpl_stats[sp][0 if got else 1] += 1
                if got and sp not in learned:
                    learned.insert(0, sp)
            if got:
                return got
        return None

    todo = [it for it in pend if not links[it["name"]]["url"]]
    real = []
    for it in todo:
        if bd.DEMO_RX.search(it["name"]) or it.get("type") == "registry:example":
            links[it["name"]]["method"] = "companion"
        else:
            real.append(it)
    slashed = [it for it in real if "/" in it["name"]]
    real_plain = [it for it in real if "/" not in it["name"]]
    # learning phase (sequential): full scans for the first few, templates only after
    for k, it in enumerate(real_plain[:FULL_SCAN_BUDGET + 10]):
        got = try_item(it, full_scan=k < FULL_SCAN_BUDGET)
        if got:
            links[it["name"]] = {"url": got, "method": "template"}
    def probe_all(batch):
        if batch and any(templates_for(it.get("type", "")) for it in batch[:1]):
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                for it, got in zip(batch, ex.map(lambda i: try_item(i, False), batch)):
                    if got:
                        links[it["name"]] = {"url": got, "method": "template"}
    probe_all(real_plain[FULL_SCAN_BUDGET + 10:])

    # variants (`fill/accessibility`, `two-tone/accessibility`) live on their base item's page
    known = {i["name"]: i["url"] for i in items if i.get("url") and i.get("linkMethod") != "pending"}
    known.update({n: v["url"] for n, v in links.items() if v["url"]})
    for it in slashed:
        base = known.get(it["name"].split("/")[-1])
        if base:
            links[it["name"]] = {"url": base, "method": "variant-page"}
    probe_all([it for it in slashed if not links[it["name"]]["url"]])

    # 3. shared-page fallback / no-page
    stem = lambda n: re.sub(r"[-_]?\d+$", "", n.split("/")[-1])
    by_stem = defaultdict(Counter)
    for i in items:
        if i.get("linkMethod") == "shared-page" and i.get("url"):
            by_stem[stem(i["name"])][i["url"]] += 1
    for it in real:
        L = links[it["name"]]
        if L["url"]:
            continue
        sc = by_stem.get(stem(it["name"]))
        if sc:
            u, n = sc.most_common(1)[0]
            if n >= 2 and n >= 0.8 * sum(sc.values()):
                links[it["name"]] = {"url": u, "method": "shared-page"}
                continue
        c = shared.get(it.get("type", ""))
        if c:
            u, n = c.most_common(1)[0]
            if n >= 3 and n >= 0.8 * sum(c.values()):
                links[it["name"]] = {"url": u, "method": "shared-page"}
                continue
        L["method"] = "no-page"

    out = {"handle": handle, "pending": len(pend), "poolSize": len(pool),
           "linked": sum(1 for v in links.values() if v["url"]),
           "methodCounts": dict(Counter(v["method"] for v in links.values())),
           "templates": {f"{h}{p}{{name}}": s for (h, p), s in tmpl_stats.items() if s[0]},
           "links": links}
    json.dump(out, open(f"{OUT}/{handle[1:]}.json", "w"), ensure_ascii=False)
    return out

def merge():
    enr = json.load(open(ENR))
    filled = Counter()
    for r in enr["registries"]:
        fp = f"{OUT}/{r['handle'][1:]}.json"
        if not os.path.exists(fp):
            continue
        L = json.load(open(fp))["links"]
        c = r["components"]
        for it in c["items"]:
            if it.get("linkMethod") == "pending" and it["name"] in L:
                it["url"] = L[it["name"]]["url"]
                it["linkMethod"] = L[it["name"]]["method"]
                filled[it["linkMethod"]] += 1
        c["exactLinks"] = link_stats(c["items"], (c.get("exactLinks") or {}).get("template"))
    found = [r for r in enr["registries"] if r["components"]["found"]]
    real = sum(r["components"].get("exactLinks", {}).get("realItems", 0) for r in found)
    rl = sum(r["components"].get("exactLinks", {}).get("realLinked", 0) for r in found)
    allit = [i for r in found for i in r["components"]["items"]]
    enr["exactLinkSummary"] = {"realItems": real, "realLinked": rl,
                               "realCoverage": round(100 * rl / max(1, real)),
                               "itemsLinkedTotal": sum(1 for i in allit if i.get("url"))}
    json.dump(enr, open(ENR, "w"), indent=2, ensure_ascii=False)
    left = sum(1 for i in allit if i.get("linkMethod") == "pending")
    print(f"filled {sum(filled.values())} pending items {dict(filled)} | still pending {left} | "
          f"real coverage {enr['exactLinkSummary']['realCoverage']}% ({rl:,}/{real:,})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        return merge()
    os.makedirs(OUT, exist_ok=True)
    regs = [r for r in json.load(open(ENR))["registries"] if pending_of(r)]
    if a.only:
        regs = [r for r in regs if r["handle"] in a.only]
    if not a.force:
        regs = [r for r in regs if not os.path.exists(f"{OUT}/{r['handle'][1:]}.json")]
    regs.sort(key=lambda r: -len(pending_of(r)))      # big ones first
    print(f"deep-linking {sum(len(pending_of(r)) for r in regs)} pending items in {len(regs)} registries", flush=True)
    t0, done = time.time(), 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(process, r): r["handle"] for r in regs}
        for f in concurrent.futures.as_completed(futs):
            h = futs[f]; done += 1
            try:
                o = f.result()
                print(f"  [{done}/{len(regs)}] {h:<26} {o['linked']}/{o['pending']} linked {o['methodCounts']} "
                      f"({time.time()-t0:.0f}s)", flush=True)
            except Exception as e:
                print(f"  ! {h}: {type(e).__name__}: {str(e)[:120]}", flush=True)
    print(f"done in {time.time()-t0:.0f}s", flush=True)

if __name__ == "__main__":
    main()
