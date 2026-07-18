#!/usr/bin/env python3
"""Generate README.md with links to every registry catalogued from the shadcn directory."""
import json, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

e = json.load(open("data/registries.enriched.json"))
try:
    PAGES = json.load(open("data/raw/pages.json"))
except FileNotFoundError:
    PAGES = {}
regs = sorted(e["registries"], key=lambda r: r["handle"].lstrip("@").lower())

def links_for(handle, homepage):
    """Markdown for the direct browse-page link(s); fall back to homepage."""
    pl = PAGES.get(handle)
    if pl:
        return " · ".join(f'[{p["label"]}]({p["url"]})' for p in pl)
    return f"[Home]({homepage})"
found = [r for r in regs if r["components"]["found"]]
notfound = [r for r in regs if not r["components"]["found"]]

REASON = {
    "dead": "site unreachable",
    "gated": "registry gated (auth)",
    "not_found": "no registry found (parked/portfolio/renamed)",
    "no-index": "items exist but not enumerable",
}

L = []
L.append("# shadcn/ui Community Registry Explorer\n")
L.append("A catalogue of every community registry listed in the "
         "[shadcn/ui Registry Directory](https://ui.shadcn.com/docs/directory), "
         "with the components each one provides.\n")
L.append(f"- **Registries catalogued:** {e['count']}")
L.append(f"- **With components found:** {e['componentsFound']}")
L.append(f"- **Total components/items:** {e['totalComponents']:,}")
L.append(f"- **Captured:** {e['capturedAt']}")
L.append("\nData files: [`data/registries.json`](data/registries.json) (directory index) · "
         "[`data/registries.enriched.json`](data/registries.enriched.json) (with components) · "
         "[`REPORT.md`](REPORT.md) (found/not-found report).\n")
L.append("Install any component with `npx shadcn add @<registry>/<component>`.\n")

L.append("---\n")
L.append(f"## Registries with components ({len(found)})\n")
L.append("The **Exact links** column shows how many *real* components have a verified "
         "direct deep link (click → land on that component). Per-component URLs live in "
         "`data/registries.enriched.json` (each item's `url` + `linkMethod`); see "
         "[`DEEPLINKS_REPORT.md`](DEEPLINKS_REPORT.md).\n")
L.append("| # | Registry | Browse components / blocks | Type | Components | Exact links |")
L.append("|---:|---|---|---|---:|---:|")
for i, r in enumerate(found, 1):
    c = r["components"]
    el = c.get("exactLinks") or {}
    if el.get("realItems"):
        exact = f'{el["realLinked"]}/{el["realItems"]} ({el["realCoverage"]}%)'
    else:
        exact = "—"
    L.append(f'| {i} | `{r["handle"]}` | {links_for(r["handle"], r["homepage"])} '
             f'| {c["terminology"] or "—"} | {c["count"]} | {exact} |')

L.append(f"\n## Registries without discoverable components ({len(notfound)})\n")
L.append("| Registry | Repository / Site | Reason |")
L.append("|---|---|---|")
for r in notfound:
    reason = REASON.get(r["components"].get("reason"), r["components"].get("reason") or "unresolved")
    L.append(f'| `{r["handle"]}` | [{r["homepage"]}]({r["homepage"]}) | {reason} |')

L.append("\n---\n")
L.append("_Links point directly to each registry's components/blocks browsing page "
         "(both are shown when a registry has a separate page for each). A few registries "
         "with no standalone index page deep-link to a representative item, from which the "
         "site's own navigation lists the rest._\n")

open("README.md", "w").write("\n".join(L) + "\n")
print(f"wrote README.md — {len(found)} found + {len(notfound)} not-found = {len(regs)} registries linked")
