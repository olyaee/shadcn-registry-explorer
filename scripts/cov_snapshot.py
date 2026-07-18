#!/usr/bin/env python3
"""Print '<linked> <real>' across the low-coverage set (for a settle-watch loop)."""
import json, re
enr = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}
REAL = {"registry:ui","registry:component","registry:block","registry:page","registry:icon","registry:theme"}
DEMO = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)
low = [h for b in json.load(open("data/raw/lowcov/batches.json")) for h in b]
tl = tr = 0
for h in low:
    try:
        d = json.load(open(f"data/raw/deeplinks/{h.lstrip('@')}.json"))
    except Exception:
        continue
    links = d.get("links", {})
    types = {it["name"]: it.get("type","") for it in enr[h]["components"]["items"]}
    real = [n for n in links if types.get(n) in REAL and not DEMO.search(n)]
    tl += sum(1 for n in real if links[n].get("url"))
    tr += len(real)
print(f"{tl} {tr}")
