#!/usr/bin/env python3
"""Fold enriched descriptions + structured fields back into registries.enriched.json.
Non-destructive: keeps the registry's own text as `descriptionOriginal`.

An enrichment line is applied only when its `src` matches the item's current source
text (legacy lines without `src` always match), so stale enrichments never land.
Items still lacking a match keep their previous values; `needsEnrichment` stays set
on new/changed items until a matching line exists.

Usage: python scripts/merge_enrichment.py [--model gpt-6-sol] [--pending]
  --model    read data/enrichment/enriched_items.<model>.jsonl (default: legacy enriched_items.jsonl)
  --pending  only touch items flagged `needsEnrichment`"""
import sys, json, os
from collections import Counter
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PENDING = "--pending" in sys.argv
MODEL = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else None
SRC = f"data/enrichment/enriched_items.{MODEL}.jsonl" if MODEL else "data/enrichment/enriched_items.jsonl"

enr = json.load(open("data/registries.enriched.json"))
E = {}
with open(SRC) as f:
    for line in f:
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id") and d.get("description"):
            E[d["id"]] = d                      # later lines win

updated = miss = 0
cats = Counter()
for r in enr["registries"]:
    if not r["components"]["found"]:
        continue
    for it in r["components"]["items"]:
        if PENDING and not it.get("needsEnrichment"):
            continue
        e = E.get(f'{r["handle"]}/{it["name"]}')
        if e and "src" in e and e["src"] != (it.get("descriptionOriginal", it.get("description")) or "")[:300]:
            e = None                            # enrichment predates the current source text
        if not e:
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
        if e.get("model"):
            it["enrichedBy"] = e["model"]
        it.pop("needsEnrichment", None)
        cats[it["category"]] += 1
        updated += 1

allit = [i for r in enr["registries"] for i in r["components"]["items"]]
allcats = Counter(i.get("category") for i in allit if i.get("category"))
enr["pendingEnrichment"] = sum(1 for i in allit if i.get("needsEnrichment"))
enr["enrichment"] = {"model": MODEL or "gpt-4o-mini", "updated": updated,
                     "byModel": dict(Counter(i.get("enrichedBy", "gpt-4o-mini") for i in allit)),
                     "missing": enr["pendingEnrichment"], "distinctCategories": len(allcats)}
json.dump(enr, open("data/registries.enriched.json", "w"), indent=2, ensure_ascii=False)
print(f"applied {updated} from {SRC} | unmatched {miss} | still pending {enr['pendingEnrichment']} | "
      f"distinct categories {len(allcats)}")
print("top 25 categories:")
for c, n in allcats.most_common(25):
    print(f"  {n:>5}  {c}")
