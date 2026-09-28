"""MCP server: `shadcn-explorer-mcp` (stdio). Data downloads in the background on first start."""
import threading, time
from mcp.server.mcpserver import MCPServer
from . import data, graph, search

INSTRUCTIONS = """Find shadcn/ui community components (~76k items, 394 registries) for a feature the user is building.
Goal: a verified shortlist covering EVERY UI piece.
1. Coverage map: list every UI piece the feature needs, phrased as what it does or looks like
   ("grouped bar chart comparing a metric across groups", not "chart"). Walk: shell & nav, data display,
   inputs & filters, overlays, feedback & empty/loading/error states, flow & progress, motion, domain specifics.
2. search_components with ALL pieces in one call (kind ["component","block"] unless the user wants otherwise).
3. Widen strong hits: browse_category (every library's version), find_similar (look-alikes elsewhere).
4. Verify: description fits; prefer items with a url; flags mark non-React, stale or unavailable libraries.
5. Deliver per piece 1-3 options: install command, doc link, why. End with a combination favouring 1-2 libraries.
Done when every piece has a recommendation or "no match -> shadcn/ui core / build"."""

server = MCPServer(name="shadcn-explorer", instructions=INSTRUCTIONS)
_ready = threading.Event()


def _download():
    data.ensure(only=["registries.enriched", "graph/"], log=False)   # enough for keyword search + graph
    _ready.set()
    data.ensure(log=False)                                             # then the semantic index


def _wait():
    if not _ready.wait(timeout=45):
        raise RuntimeError("The catalogue is still downloading on first start (~65 MB). Retry in a minute.")


def _compact(r):
    return {k: r.get(k) for k in ("install", "url", "description", "kind", "category", "cosine")
            if r.get(k) is not None} | ({"flags": fl} if (fl := search.flags(r)) else {})


@server.tool()
def search_components(pieces: dict[str, str], kind: list[str] | None = None, k: int = 6,
                      per_registry: int = 2) -> dict:
    """Search the catalogue for every UI piece at once. `pieces` maps a short piece name to a query phrased as
    what the component does or looks like. `kind` filters: component, block, hook, page, template, icon, logo,
    font, theme, utility. Returns up to k options per piece (max per_registry per library)."""
    _wait()
    res = search.search(pieces, kind or [], None, k, per_registry)
    return {"mode": res["mode"], "note": res["note"],
            "results": {p: [_compact(r) for r in rows] for p, rows in res["results"].items()}}


@server.tool()
def browse_category(label: str, kind: list[str] | None = None, per_registry: int = 2) -> dict:
    """Every library's version of one component type, e.g. "Kanban Board". Use list_categories to find labels."""
    _wait()
    res = graph.category(label, kind or [], per_registry)
    if not res:
        return {"error": f'no category matching "{label}" — try list_categories(grep=...)'}
    return {"category": res["category"]["label"], "description": res["category"]["description"],
            "itemCount": res["itemCount"], "otherMatches": res["otherMatches"],
            "registries": {h: [_compact(r) for r in rows] for h, rows in res["registries"].items()}}


@server.tool()
def list_categories(grep: str | None = None, top: int = 30) -> list:
    """Category labels of the component graph (clusters of equivalent components across libraries)."""
    _wait()
    return [{"label": c["label"], "items": c["itemCount"], "registries": c["registryCount"],
             "description": c["description"]} for c in graph.categories(grep, None, top)]


@server.tool()
def find_similar(item: str, k: int = 10, other_registries: bool = True) -> list | dict:
    """Items most similar to `item` (format @handle/name), by embedding. Offline — no API key needed."""
    _wait()
    res = graph.similar(item, k, other_registries)
    if res is None:
        return {"error": f"{item} not found, or the search index is still downloading"}
    return [_compact(r) for r in res]


@server.tool()
def registry_info(handle: str) -> dict:
    """What one library (e.g. @reui) is, its health, framework and which categories it covers."""
    _wait()
    res = graph.registry(handle)
    if not res:
        return {"error": f"unknown registry {handle}"}
    r = res["registry"]
    return {k: r.get(k) for k in ("handle", "description", "framework", "componentCount", "health",
                                   "active", "browseUrl")} | {"categories": res["categories"][:40]}


def main():
    threading.Thread(target=_download, daemon=True).start()
    server.run("stdio")


if __name__ == "__main__":
    main()
