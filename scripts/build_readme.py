#!/usr/bin/env python3
"""Generate README.md (concise) and REGISTRIES.md (every registry with browse links)."""
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

R = [
    "# shadcn Registry Explorer\n",
    f"Find shadcn/ui components for what you're building — {e['totalComponents']:,} items from "
    f"{e['count']} community registries (updated {e['capturedAt']}).\n",
    "## Install\n",
    "**As an MCP server** (Claude Code, Cursor, Codex, …; needs [uv](https://docs.astral.sh/uv/)):\n",
    "```bash\nclaude mcp add shadcn-explorer -s user -e OPENAI_API_KEY=sk-... -- \\\n"
    "  uvx --from git+https://github.com/olyaee/shadcn-registry-explorer shadcn-explorer-mcp\n```\n",
    "Other clients: command `uvx`, args `--from git+https://github.com/olyaee/shadcn-registry-explorer "
    "shadcn-explorer-mcp`, env `OPENAI_API_KEY` (optional). Then ask: *\"find components to build a fairness "
    "dashboard\"*. Data (~260 MB) downloads in the background on first start.\n",
    "**Or clone** and point any agent at the folder ([`AGENTS.md`](AGENTS.md)), or search yourself: "
    "`./find \"grouped bar chart\"`, `./find graph category \"Kanban Board\"`.\n",
    "## How it works\n",
    "![How it works](docs/architecture.png)\n",
    "- **Search** ranks items by meaning and keywords. The OpenAI key is optional: it embeds your query "
    "(fraction of a cent) so \"billing toggle\" also finds a \"monthly/annual switch\"; without it, "
    "search matches keywords only.\n"
    "- **Graph** groups equivalent components across libraries, so `find graph` lists every version of one.\n",
    "[All registries](REGISTRIES.md) · [MIT](LICENSE) — components belong to their authors.\n",
]
open("README.md", "w").write("\n".join(R) + "\n")

L = []
L.append("# Registries\n")
L.append(f"{e['count']} registries from the [shadcn directory](https://ui.shadcn.com/docs/directory) · "
         f"last refresh: [`MCP_REFRESH_REPORT.md`](MCP_REFRESH_REPORT.md).\n")
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

open("REGISTRIES.md", "w").write("\n".join(L) + "\n")
print(f"wrote README.md + REGISTRIES.md — {len(found)} found + {len(notfound)} not-found = {len(regs)} registries linked")
