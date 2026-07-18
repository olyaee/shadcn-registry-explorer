#!/usr/bin/env python3
"""
Merge the base registry list + authoritative index crawl + agent recovery files
into one enriched dataset, and emit a found/not-found report.

Inputs:
  data/registries.json            (238 base registries)
  data/raw/index_probe.json       (210 with machine-readable index)
  data/raw/recover/agent_*.json   (recovery for the 28 without a standard index)

Outputs:
  data/registries.enriched.json
  REPORT.md
"""
import json, glob, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TYPE_LABEL = {
    "registry:block": "Blocks",
    "registry:ui": "Components",
    "registry:component": "Components",
    "registry:hook": "Hooks",
    "registry:page": "Pages",
    "registry:template": "Templates",
    "registry:theme": "Themes",
    "registry:style": "Themes",
    "registry:icon": "Icons",
    "registry:lib": "Utilities",
    "registry:file": "Files",
}

def terminology(items):
    types = [i.get("type", "") for i in items if i.get("type")]
    if not types:
        return "Items"
    c = Counter(types).most_common()
    top, topn = c[0]
    label = TYPE_LABEL.get(top, "Components")
    if len(c) > 1:
        second, secn = c[1]
        if secn >= 0.4 * topn:
            l2 = TYPE_LABEL.get(second, None)
            if l2 and l2 != label:
                label = f"{label} & {l2}"
    return label

# ---- load base ----
base = json.load(open("data/registries.json"))
registries = {r["handle"]: dict(r) for r in base["registries"]}

# ---- load index crawl ----
index_probe = json.load(open("data/raw/index_probe.json"))
by_handle_index = {r["handle"]: r for r in index_probe}

# ---- load agent recovery ----
STATUS_RANK = {"found": 3, "partial": 2, "gated": 1, "not_found": 0, "dead": 0, None: 0}
def better(a, b):
    """Return the stronger of two recovery records for the same handle."""
    if a is None: return b
    if b is None: return a
    ka = (STATUS_RANK.get(a.get("status"), 0), len(a.get("items") or []))
    kb = (STATUS_RANK.get(b.get("status"), 0), len(b.get("items") or []))
    return a if ka >= kb else b

recovered = {}
term_hint = {}
note_hint = {}
for fp in sorted(glob.glob("data/raw/recover/*.json")):
    try:
        arr = json.load(open(fp))
    except Exception as e:
        print(f"  ! skipping {fp}: {e}")
        continue
    for row in arr:
        h = row["handle"]
        recovered[h] = better(recovered.get(h), row)
        if row.get("terminology") and h not in term_hint:
            term_hint[h] = row["terminology"]
        # keep the most informative note across all sources
        n = (row.get("notes") or "").strip()
        if n and len(n) > len(note_hint.get(h, "")):
            note_hint[h] = n

# ---- merge ----
for handle, reg in registries.items():
    comp = {"found": False, "source": None, "indexUrl": None,
            "terminology": None, "count": 0, "items": []}
    idx = by_handle_index.get(handle)
    rec = recovered.get(handle)

    if idx and idx.get("status") == "found":
        items = idx["items"]
        comp.update(found=True, source="registry-index", indexUrl=idx["indexUrl"],
                    terminology=terminology(items), count=len(items), items=items)
    elif rec and rec.get("status") in ("found", "partial") and rec.get("items"):
        items = [{"name": it.get("name"), "type": it.get("type", ""),
                  "title": it.get("title", ""), "description": it.get("description", "")}
                 for it in rec["items"]]
        comp.update(found=True, source="site-recovery",
                    indexUrl=rec.get("indexUrl"),
                    terminology=rec.get("terminology") or terminology(items),
                    count=len(items), items=items,
                    recoveryStatus=rec.get("status"), method=rec.get("method"))
    else:
        # unresolved
        reason = None
        if rec:
            reason = rec.get("status")  # dead / gated / not_found
            comp["terminology"] = rec.get("terminology") or term_hint.get(handle)
            comp["notes"] = rec.get("notes")
        elif idx:
            reason = "no-index"
        comp["reason"] = reason
    reg["components"] = comp

out_list = [registries[h] for h in sorted(registries, key=lambda x: x.lower())]
found = [r for r in out_list if r["components"]["found"]]
notfound = [r for r in out_list if not r["components"]["found"]]
total_items = sum(r["components"]["count"] for r in found)

enriched = {
    "source": base["source"],
    "capturedAt": base["capturedAt"],
    "count": len(out_list),
    "componentsFound": len(found),
    "componentsNotFound": len(notfound),
    "totalComponents": total_items,
    "registries": out_list,
}
json.dump(enriched, open("data/registries.enriched.json", "w"), indent=2, ensure_ascii=False)

# ---- report ----
def reason_label(r):
    c = r["components"]
    rs = c.get("reason")
    return {
        "dead": "site unreachable (DNS/connection)",
        "gated": "registry gated (auth required)",
        "not_found": "no component listing found on site",
        "no-index": "items exist but no enumerable index",
        None: "unresolved",
    }.get(rs, rs)

lines = []
lines.append("# shadcn Community Registries — Component Inventory Report\n")
lines.append(f"- **Source:** {base['source']}")
lines.append(f"- **Captured:** {base['capturedAt']}")
lines.append(f"- **Registries:** {len(out_list)}")
lines.append(f"- **With components found:** {len(found)}")
lines.append(f"- **Without components:** {len(notfound)}")
lines.append(f"- **Total components catalogued:** {total_items:,}\n")

lines.append("## ✅ Registries with components found\n")
lines.append("| Registry | Calls them | # items | Source |")
lines.append("|---|---|---:|---|")
for r in sorted(found, key=lambda x: -x["components"]["count"]):
    c = r["components"]
    lines.append(f'| {r["handle"]} | {c["terminology"] or "—"} | {c["count"]} | {c["source"]} |')

lines.append("\n## ❌ Registries without discoverable components\n")
if notfound:
    lines.append("| Registry | Homepage | Reason | Diagnosis |")
    lines.append("|---|---|---|---|")
    for r in sorted(notfound, key=lambda x: x["handle"].lower()):
        note = (note_hint.get(r["handle"], "") or "").replace("|", "/")[:160]
        lines.append(f'| {r["handle"]} | {r["homepage"]} | {reason_label(r)} | {note} |')
else:
    lines.append("_None — every registry yielded components._")

open("REPORT.md", "w").write("\n".join(lines) + "\n")

print(f"registries          : {len(out_list)}")
print(f"components found     : {len(found)}")
print(f"components not found : {len(notfound)}")
print(f"total components     : {total_items}")
print(f"recovery files loaded: {len(recovered)} handles")
print("wrote data/registries.enriched.json and REPORT.md")
