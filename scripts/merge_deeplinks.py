#!/usr/bin/env python3
"""Merge per-item deep links into registries.enriched.json and emit a coverage report."""
import json, os, glob
from collections import Counter
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

enr = json.load(open("data/registries.enriched.json"))
dl = {}
for fp in glob.glob("data/raw/deeplinks/*.json"):
    d = json.load(open(fp))
    dl[d["handle"]] = d

REAL_TYPES = {"registry:ui", "registry:component", "registry:block", "registry:page",
              "registry:icon", "registry:theme"}
total_real = total_linked = total_items_linked = 0
rows = []
for r in enr["registries"]:
    c = r["components"]
    if not c["found"]:
        continue
    d = dl.get(r["handle"])
    if not d:
        c["exactLinks"] = {"status": "pending"}
        continue
    links = d.get("links", {})
    import re as _re
    DEMO = _re.compile(r"-(demos?|examples?|preview)(-\d+)?$", _re.I)
    real = real_linked = linked_total = 0
    methods = Counter()
    for it in c["items"]:
        L = links.get(it["name"], {}) or {}
        it["url"] = L.get("url")
        it["linkMethod"] = L.get("method", "none")
        methods[it["linkMethod"]] += 1
        if it["url"]:
            linked_total += 1
        is_real = it.get("type") in REAL_TYPES and not DEMO.search(it["name"])
        if is_real:
            real += 1
            if it["url"]:
                real_linked += 1
    cov = round(100 * real_linked / max(1, real))
    c["exactLinks"] = {
        "realItems": real, "realLinked": real_linked, "realCoverage": cov,
        "template": d.get("templateStr"), "linkedTotal": linked_total,
        "methods": dict(methods),
    }
    total_real += real; total_linked += real_linked
    total_items_linked += linked_total
    rows.append((r["handle"], real_linked, real, cov, d.get("templateStr"), dict(methods)))

enr["exactLinkSummary"] = {
    "realItems": total_real, "realLinked": total_linked,
    "realCoverage": round(100 * total_linked / max(1, total_real)),
    "itemsLinkedTotal": total_items_linked,
}
json.dump(enr, open("data/registries.enriched.json", "w"), indent=2, ensure_ascii=False)

# report
rows.sort(key=lambda x: (x[3], x[2]))   # worst coverage first
L = ["# Per-Component Deep-Link Coverage\n",
     f"- **Registries processed:** {len(rows)}",
     f"- **Real component items:** {total_real:,}",
     f"- **With a verified exact link:** {total_linked:,} ({enr['exactLinkSummary']['realCoverage']}%)",
     f"- **Total items linked (incl. non-'real' types):** {total_items_linked:,}\n",
     "`method`: sitemap / crawl (real hrefs) / template (HTTP-verified guess) / "
     "companion (demo/example — expected no page) / no-page (verified absent).\n",
     "## Registries by coverage (lowest first)\n",
     "| Registry | Real linked | Coverage | Template | Methods |",
     "|---|---:|---:|---|---|"]
for h, rl, ri, cov, tmpl, mc in rows:
    L.append(f"| {h} | {rl}/{ri} | {cov}% | {tmpl or '—'} | {mc} |")
open("DEEPLINKS_REPORT.md", "w").write("\n".join(L) + "\n")
print(f"merged {len(rows)} registries | real coverage {enr['exactLinkSummary']['realCoverage']}% "
      f"({total_linked:,}/{total_real:,}) | wrote DEEPLINKS_REPORT.md")
