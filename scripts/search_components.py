#!/usr/bin/env python3
"""Search the catalogued components for fits against the Availability/Gantt brief."""
import json, re
enr = json.load(open("data/registries.enriched.json"))
try:
    PAGES = json.load(open("data/raw/pages.json"))
except FileNotFoundError:
    PAGES = {}

# (category, weight, regex) — matched against "name + description"
CATS = [
    ("Gantt / resource timeline", 100, r"\bgantt\b|resource[- ]?plann|resource[- ]?timeline|swimlane|\bplanner\b|roadmap"),
    ("Scheduler / rota / shifts",   90, r"schedul|\brota\b|roster|\bshift(s)?\b|appointment|booking|reservation|time[- ]?slot|availabilit"),
    ("Timeline",                    70, r"\btimeline\b|time[- ]?axis"),
    ("Big / range calendar",        75, r"big[- ]?calendar|full[- ]?calendar|event[- ]?calendar|range[- ]?calendar|calendar[- ]?range|month[- ]?view|week[- ]?view|day[- ]?view|multi[- ]?month"),
    ("Calendar / date-range",       55, r"\bcalendar\b|date[- ]?range|date[- ]?picker|range[- ]?picker"),
    ("Data grid (sticky/frozen/virtual)", 80, r"data[- ]?grid|datagrid|data[- ]?table|datatable|spreadsheet|frozen|pinned|sticky[- ]?column|virtual|tanstack|ag[- ]?grid"),
    ("Kanban / board / DnD",        50, r"\bkanban\b|\bboard\b|drag[- ]?and[- ]?drop|\bdnd\b|sortable|draggable"),
    ("Heatmap / coverage",          65, r"heat[- ]?map|contribution[- ]?graph|activity[- ]?calendar|calendar[- ]?heatmap"),
    ("Controls (zoom/segment/filter)", 30, r"segmented|toggle[- ]?group|\bzoom\b|command[- ]?menu|\bcombobox\b|faceted|data[- ]?table[- ]?toolbar"),
]

def link(handle):
    pl = PAGES.get(handle)
    if pl: return pl[0]["url"]
    return None

rows = []
for r in enr["registries"]:
    if not r["components"]["found"]:
        continue
    for it in r["components"]["items"]:
        text = f'{it.get("name","")} {it.get("title","")} {it.get("description","")}'.lower()
        for cat, w, rx in CATS:
            if re.search(rx, text):
                rows.append({
                    "cat": cat, "w": w, "handle": r["handle"],
                    "name": it.get("name"), "type": it.get("type",""),
                    "desc": (it.get("description") or "")[:140],
                    "link": link(r["handle"]),
                })
                break  # first (highest-priority) category wins

# group by category, sort within by weight then registry
from collections import defaultdict
bycat = defaultdict(list)
for x in rows:
    bycat[x["cat"]].append(x)

order = [c[0] for c in CATS]
for cat in order:
    items = bycat.get(cat, [])
    if not items: continue
    print(f"\n{'='*70}\n{cat}  ({len(items)} matches)\n{'='*70}")
    # dedupe by (handle,name)
    seen=set(); uniq=[]
    for x in items:
        k=(x["handle"],x["name"])
        if k in seen: continue
        seen.add(k); uniq.append(x)
    for x in uniq[:18]:
        print(f'  {x["handle"]:<20} {x["name"]:<28} [{x["type"].replace("registry:","")}] {x["desc"]}')
    if len(uniq)>18:
        print(f'  ... +{len(uniq)-18} more')

# summary counts
print("\n\nSUMMARY (unique registry+item per category):")
for cat in order:
    items=bycat.get(cat,[])
    u=len(set((x["handle"],x["name"]) for x in items))
    if u: print(f"  {u:>4}  {cat}")
