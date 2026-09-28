#!/usr/bin/env python3
"""
Refresh data/registries.enriched.json from the shadcn MCP harvest.

Sources (priority per registry):
  1. data/raw/mcp/<handle>.json           shadcn MCP `list_items_in_registries` (scripts/mcp_harvest.mjs)
  2. data/raw/mcp_fallback/<handle>.json  lenient direct index fetch (scripts/fetch_index_fallback.py)
  3. existing items in registries.enriched.json, kept and flagged `stale`
Registry list/meta: data/raw/public_registries_index.json (https://ui.shadcn.com/r/registries.json).

Per item, matched by name (also `<registry>-<name>` renames):
  - carried over: title, url, linkMethod, enriched fields (description/category/tags/kind/useCases/style)
  - descriptionOriginal <- current source description
  - new items, or items whose source description changed, get `needsEnrichment: true`
    (their `description` is the source text until scripts/enrich_descriptions.py --pending runs)
Items that disappeared upstream are dropped (logged in data/raw/mcp_changes.json).

Usage: python scripts/update_from_mcp.py [--baseline PATH]
  --baseline  the pre-refresh dataset to diff/carry over from (default: registries.enriched.json itself;
              pass the previous capture, e.g. `git show <rev>:data/registries.enriched.json > /tmp/base.json`,
              when re-running after a refresh has already been written)
"""
import json, os, sys, re, datetime
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "scripts")
from parse_mcp import load_all

ENR = "data/registries.enriched.json"
TODAY = datetime.date.today().isoformat()
# Aggregators that mirror other registries' items — catalogue the registry, not its items.
MIRRORS = {"@registrydirectory"}
ENRICHED_FIELDS = ("category", "tags", "kind", "useCases", "style")

TYPE_LABEL = {
    "registry:block": "Blocks", "registry:ui": "Components", "registry:component": "Components",
    "registry:hook": "Hooks", "registry:page": "Pages", "registry:template": "Templates",
    "registry:theme": "Themes", "registry:style": "Themes", "registry:icon": "Icons",
    "registry:lib": "Utilities", "registry:file": "Files",
}

def terminology(items):
    c = Counter(i.get("type") for i in items if i.get("type")).most_common()
    if not c:
        return "Items"
    label = TYPE_LABEL.get(c[0][0], "Components")
    if len(c) > 1 and c[1][1] >= 0.4 * c[0][1]:
        l2 = TYPE_LABEL.get(c[1][0])
        if l2 and l2 != label:
            label = f"{label} & {l2}"
    return label

REAL_TYPES = {"registry:ui", "registry:component", "registry:block", "registry:page",
              "registry:icon", "registry:theme"}
DEMO = re.compile(r"-(demos?|examples?|preview)(-\d+)?$", re.I)

def link_stats(items, template):
    real = [i for i in items if i.get("type") in REAL_TYPES and not DEMO.search(i["name"])]
    real_linked = sum(1 for i in real if i.get("url"))
    return {"realItems": len(real), "realLinked": real_linked,
            "realCoverage": round(100 * real_linked / max(1, len(real))),
            "template": template, "linkedTotal": sum(1 for i in items if i.get("url")),
            "methods": dict(Counter(i.get("linkMethod", "none") for i in items))}

def merge_items(handle, reg_name, src_items, old_items):
    old_by = {i["name"]: i for i in old_items}
    out, seen, stats = [], set(), Counter()
    for s in src_items:
        name = s["name"]
        if not name or name in seen:
            stats["duplicate"] += 1
            continue
        seen.add(name)
        o = old_by.get(name) or old_by.get(f"{reg_name}-{name}")
        src_desc = s.get("description") or ""
        if o:
            it = dict(o)
            it["name"] = name
            it["type"] = s.get("type") or o.get("type", "")
            if s.get("title"):
                it["title"] = s["title"]
            changed = src_desc != (o.get("descriptionOriginal") or "")
            it["descriptionOriginal"] = src_desc
            if changed:
                it["needsEnrichment"] = True
                stats["descChanged"] += 1
            else:
                stats["unchanged"] += 1
            if o["name"] != name:
                stats["renamed"] += 1
        else:
            it = {"name": name, "type": s.get("type", ""), "title": s.get("title", ""),
                  "description": src_desc, "url": None, "linkMethod": "pending",
                  "descriptionOriginal": src_desc, "category": "", "tags": [], "kind": "",
                  "useCases": [], "style": [], "needsEnrichment": True}
            stats["added"] += 1
        out.append(it)
    matched = {n for n in seen} | {f"{reg_name}-{n}" for n in seen}
    removed = [n for n in old_by if n not in matched]
    stats["removed"] = len(removed)
    return out, stats, removed

def main():
    base = sys.argv[sys.argv.index("--baseline") + 1] if "--baseline" in sys.argv else ENR
    enr = json.load(open(base))
    old = {r["handle"]: r for r in enr["registries"]}
    index = {r["name"]: r for r in json.load(open("data/raw/public_registries_index.json"))
             if r["name"] != "@shadcn"}
    mcp = load_all()
    fb = {}
    fb_dir = "data/raw/mcp_fallback"
    for f in os.listdir(fb_dir) if os.path.isdir(fb_dir) else []:
        d = json.load(open(os.path.join(fb_dir, f)))
        if d["ok"]:
            fb[d["handle"]] = d

    changes, out, tally = {}, [], Counter()
    for handle in sorted(set(index) | set(old), key=str.lower):
        ix, o, m = index.get(handle), old.get(handle), mcp.get(handle)
        name = handle[1:]
        reg = {"handle": handle, "name": name,
               "homepage": (ix or o)["homepage"],
               "install": f"npx shadcn add {handle}",
               "description": (ix["description"] if ix and ix.get("description") else (o or {}).get("description", "")),
               "listed": bool(ix)}
        if ix and ix.get("health"):
            h = ix["health"]
            reg["health"] = {"status": h.get("status"), "score": h.get("score"),
                             "reason": (h.get("statusReason") or {}).get("message"),
                             "checkedAt": h.get("checkedAt")}
        old_c = (o or {}).get("components", {})
        old_items = old_c.get("items", [])
        mcp_meta = {"status": "ok" if m and m["ok"] else ("error" if m else "not-queried"),
                    "error": (m or {}).get("error"), "fetchedAt": (m or {}).get("fetchedAt")}
        template = (old_c.get("exactLinks") or {}).get("template")

        if handle in MIRRORS:
            comp = {"found": False, "source": "shadcn-mcp", "indexUrl": ix["url"].replace("{name}", "registry"),
                    "terminology": "Registry mirror", "count": 0, "items": [], "reason": "mirror",
                    "notes": f"Aggregator mirroring other registries ({m['total'] if m else '?'} items); items not catalogued to avoid duplicates.",
                    "mcp": mcp_meta}
            tally["mirror"] += 1
        elif (m and m["ok"]) or handle in fb:
            via_mcp = bool(m and m["ok"])
            src = m["items"] if via_mcp else fb[handle]["items"]
            items, stats, removed = merge_items(handle, name, src, old_items)
            idx_url = (ix["url"].replace("{style}/", "").replace("{name}", "registry") if via_mcp
                       else fb[handle]["indexUrl"])
            comp = {"found": bool(items), "source": "shadcn-mcp" if via_mcp else "registry-index-direct",
                    "indexUrl": idx_url, "terminology": terminology(items) if items else None,
                    "count": len(items), "items": items, "mcp": mcp_meta, "refreshedAt": TODAY}
            if not items:
                comp["reason"] = "empty-index"
            comp["exactLinks"] = link_stats(items, template)
            changes[handle] = {"source": comp["source"], "old": len(old_items), "new": len(items),
                               **dict(stats), "removedNames": removed, "isNewRegistry": o is None}
            tally["mcp" if via_mcp else "direct"] += 1
        elif o:
            comp = dict(old_c)
            comp["stale"] = True
            comp["mcp"] = mcp_meta
            if old_c.get("found"):
                comp["notes"] = ((old_c.get("notes") or "") + " " if old_c.get("notes") else "") + \
                    f"Not refreshed on {TODAY}: registry index unreachable via MCP/direct fetch; items are from the 2026-07-18 capture."
            tally["stale"] += 1
        else:
            comp = {"found": False, "source": None, "indexUrl": None, "terminology": None, "count": 0,
                    "items": [], "reason": "no-index", "mcp": mcp_meta,
                    "notes": f"Listed in the directory but no enumerable index ({(mcp_meta['error'] or '').splitlines()[0][:160] if mcp_meta['error'] else 'unknown'})."}
            tally["new-unresolved"] += 1
        reg["components"] = comp
        out.append(reg)

    found = [r for r in out if r["components"]["found"]]
    all_items = [i for r in found for i in r["components"]["items"]]
    real = sum(r["components"].get("exactLinks", {}).get("realItems", 0) for r in found)
    real_linked = sum(r["components"].get("exactLinks", {}).get("realLinked", 0) for r in found)
    enr_new = {
        "source": "https://ui.shadcn.com/r/registries.json",
        "capturedAt": TODAY,
        "method": "shadcn MCP (npx shadcn mcp · list_items_in_registries) with direct-index fallback",
        "count": len(out),
        "componentsFound": len(found),
        "componentsNotFound": len(out) - len(found),
        "totalComponents": len(all_items),
        "pendingEnrichment": sum(1 for i in all_items if i.get("needsEnrichment")),
        "registries": out,
        "exactLinkSummary": {"realItems": real, "realLinked": real_linked,
                             "realCoverage": round(100 * real_linked / max(1, real)),
                             "itemsLinkedTotal": sum(1 for i in all_items if i.get("url"))},
        "enrichment": enr.get("enrichment"),
        "refresh": dict(tally),
    }
    json.dump(enr_new, open(ENR, "w"), indent=2, ensure_ascii=False)
    json.dump(changes, open("data/raw/mcp_changes.json", "w"), indent=1, ensure_ascii=False)

    agg = Counter()
    for c in changes.values():
        for k in ("added", "removed", "descChanged", "unchanged", "renamed", "duplicate"):
            agg[k] += c.get(k, 0)
    write_report(enr_new, changes, agg, dict(tally), set(old))
    print(f"registries {len(out)} | found {len(found)} | items {len(all_items)} | "
          f"pending enrichment {enr_new['pendingEnrichment']}")
    print("sources:", dict(tally))
    print("item changes:", dict(agg))

def write_report(e, changes, agg, tally, old_handles):
    regs = e["registries"]
    new_regs = [r["handle"] for r in regs if r["handle"] not in old_handles]
    L = ["# Registry refresh via the shadcn MCP\n",
         f"- **Refreshed:** {e['capturedAt']} from `{e['source']}`",
         f"- **Method:** {e['method']}",
         f"- **Registries:** {e['count']} ({len(new_regs)} new since the 2026-07-18 capture) · "
         f"with components: {e['componentsFound']}",
         f"- **Total items:** {e['totalComponents']:,}",
         f"- **Sources:** MCP {tally.get('mcp', 0)} · direct index fallback {tally.get('direct', 0)} · "
         f"stale (kept from previous capture) {tally.get('stale', 0)} · unresolved new {tally.get('new-unresolved', 0)} · "
         f"mirror {tally.get('mirror', 0)}",
         f"- **Item changes in refreshed registries:** +{agg['added']:,} added · −{agg['removed']:,} removed · "
         f"{agg['descChanged']:,} source descriptions changed · {agg['renamed']:,} renamed · {agg['unchanged']:,} unchanged\n",
         "Items that are new or whose source description changed are re-enriched by "
         "`scripts/enrich_descriptions.py --pending` + `scripts/merge_enrichment.py --pending`. "
         "New items have `linkMethod: \"pending\"` until the deep-link stage is re-run.\n",
         "## Refreshed registries\n",
         "| Registry | Source | Before | After | + | − | Desc changed |", "|---|---|---:|---:|---:|---:|---:|"]
    for h, c in sorted(changes.items(), key=lambda x: -(x[1].get("added", 0) + x[1].get("removed", 0))):
        L.append(f"| `{h}`{' 🆕' if c['isNewRegistry'] else ''} | {c['source']} | {c['old']} | {c['new']} | "
                 f"{c.get('added', 0)} | {c.get('removed', 0)} | {c.get('descChanged', 0)} |")
    L += ["\n## Not refreshed\n", "| Registry | In directory | Health | Items kept | Why |", "|---|---|---|---:|---|"]
    for r in regs:
        c = r["components"]
        if c.get("stale") or c.get("reason") in ("no-index", "mirror", "empty-index"):
            why = (c["mcp"].get("error") or ("delisted from directory" if not r["listed"] else c.get("reason") or "")).split("\n")[0][:140].replace("|", "/")
            L.append(f"| `{r['handle']}` | {'yes' if r['listed'] else 'no'} | {(r.get('health') or {}).get('status', '—')} | "
                     f"{c['count']} | {why} |")
    open("MCP_REFRESH_REPORT.md", "w").write("\n".join(L) + "\n")

if __name__ == "__main__":
    main()
