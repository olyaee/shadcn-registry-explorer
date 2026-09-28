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
    "empty-index": "index published but empty",
    "mirror": "aggregator mirroring other registries (items not catalogued)",
}

L = []
L.append("# shadcn/ui Community Registry Explorer\n")
L.append("> **AI agents:** follow [`AGENTS.md`](AGENTS.md).\n")
L.append(f"{e['totalComponents']:,} components from {e['componentsFound']} of the {e['count']} registries in the "
         f"[shadcn directory](https://ui.shadcn.com/docs/directory) (captured {e['capturedAt']}).\n")
L.append("Give your coding agent this repo's path and the feature you're building — or search yourself:\n")
L.append("```bash\n./find \"grouped bar chart comparing a metric across groups\"\n./find graph category \"Kanban Board\"\n```\n")
L.append("Data: `data/registries.enriched.json` (downloaded by `./find` / `scripts/fetch_data.py`) · "
         "last refresh: [`MCP_REFRESH_REPORT.md`](MCP_REFRESH_REPORT.md).\n")
L.append("---\n")
L.append(f"## Registries with components ({len(found)})\n")
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

open("README.md", "w").write("\n".join(L) + "\n")
print(f"wrote README.md — {len(found)} found + {len(notfound)} not-found = {len(regs)} registries linked")
