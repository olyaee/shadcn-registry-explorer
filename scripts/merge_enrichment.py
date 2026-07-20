#!/usr/bin/env python3
"""Fold enriched descriptions + structured fields back into registries.enriched.json.
Non-destructive: keeps the original as `descriptionOriginal`."""
import json, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

enr = json.load(open("data/registries.enriched.json"))
E = {}
with open("data/enrichment/enriched_items.jsonl") as f:
    for line in f:
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id"):
            E[d["id"]] = d

updated = miss = 0
from collections import Counter
cats = Counter()
for r in enr["registries"]:
    if not r["components"]["found"]:
        continue
    for it in r["components"]["items"]:
        e = E.get(f'{r["handle"]}/{it["name"]}')
        if not e or not e.get("description"):
            miss += 1
            continue
        if "descriptionOriginal" not in it:
            it["descriptionOriginal"] = it.get("description", "")
        it["description"] = e["description"]
        it["category"] = e.get("category", "")
        it["tags"] = e.get("tags", [])
        it["kind"] = e.get("kind", "")
        it["useCases"] = e.get("useCases", [])
        it["style"] = e.get("style", [])
        cats[it["category"]] += 1
        updated += 1

enr["enrichment"] = {"updated": updated, "missing": miss, "distinctCategories": len(cats)}
json.dump(enr, open("data/registries.enriched.json", "w"), indent=2, ensure_ascii=False)
print(f"updated {updated} items | missing {miss} | distinct categories {len(cats)}")
print("top 25 categories:")
for c, n in cats.most_common(25):
    print(f"  {n:>5}  {c}")
