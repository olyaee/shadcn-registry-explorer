"""Command line: `shadcn-explorer` (installed) or `./find` (repo checkout).

  find "query" ["query" ...] [--kind component,block] [--k 8] [--json]
  find --brief brief.json | --brief -          {"piece": "query", ...} from a file / stdin
  find graph <domains|categories|category|similar|registry> ...   (find graph --help)
  find update                                  refresh the catalogue + search index
"""
import argparse, json, sys
from . import data, graph, search


def _dump(obj):
    print(json.dumps(obj, indent=1, ensure_ascii=False))


def _row(r, extra=""):
    fl = search.flags(r)
    return (f'  {r["install"]}  [{r.get("kind") or r.get("type")}]{extra}' + (f'  ⚠ {", ".join(fl)}' if fl else "")
            + f'\n      {(r.get("description") or "")[:150]}\n      {r.get("url") or "(no page: " + str(r.get("linkMethod")) + ")"}')


def graph_main(argv):
    ap = argparse.ArgumentParser(prog="find graph", description="Browse the component graph.")
    ap.add_argument("cmd", choices=["domains", "categories", "category", "similar", "registry"])
    ap.add_argument("arg", nargs="?", help="category label, @handle/name or @handle")
    ap.add_argument("--domain"); ap.add_argument("--grep")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--kind", default="")
    ap.add_argument("--per-registry", type=int, default=3)
    ap.add_argument("--k", type=int, default=12)
    ap.add_argument("--other-registries", action="store_true")
    ap.add_argument("--include-demos", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    kinds = [k for k in a.kind.split(",") if k]

    if a.cmd == "domains":
        rows = graph.domains()
        if a.json: return _dump(rows)
        for d in rows:
            print(f'{d["id"]:<4} {d["itemCount"]:>6} items  {d["nCategories"]:>3} cats  {d["label"]} — {d["description"]}')
    elif a.cmd == "categories":
        rows = graph.categories(a.grep, a.domain, a.top)
        if a.json: return _dump(rows)
        doms = {d["id"]: d["label"] for d in graph.domains()}
        for c in rows:
            print(f'{c["id"]:<6} {c["itemCount"]:>5} items / {c["registryCount"]:>3} registries  '
                  f'{c["label"]}  [{doms.get(c["domainId"], "?")}] — {c["description"]}')
    elif a.cmd == "category":
        res = graph.category(a.arg, kinds, a.per_registry, a.include_demos)
        if not res: sys.exit(f'no category matching "{a.arg}" — try: find graph categories --grep <word>')
        if a.json: return _dump(res)
        c = res["category"]
        print(f'{c["id"]} {c["label"]} — {c["description"]}\n{res["itemCount"]} items from {len(res["registries"])} registries'
              + (f' · other matches: {", ".join(res["otherMatches"])}' if res["otherMatches"] else "") + "\n")
        for h, rows in res["registries"].items():
            print(h)
            for r in rows: print(_row(r))
    elif a.cmd == "registry":
        res = graph.registry(a.arg or "")
        if not res: sys.exit(f"unknown registry {a.arg}")
        if a.json: return _dump(res)
        r = res["registry"]
        print(f'{r["handle"]} — {r["description"]}\n  {r.get("framework", "react")} · {r["componentCount"]} items · '
              f'health {r["health"]} · {"active" if r["active"] else "INACTIVE"} · {r["browseUrl"]}\n')
        for c in res["categories"][:a.top]:
            print(f'  {c["items"]:>4}  {c["category"]}  ({c["id"]})')
    elif a.cmd == "similar":
        res = graph.similar(a.arg or "", a.k, a.other_registries, kinds, a.include_demos)
        if res is None: sys.exit(f"{a.arg} not in the search index (format @handle/name)")
        if a.json: return _dump(res)
        print(f"nearest to {a.arg}:\n")
        for r in res: print(_row(r, f'  cos={r["cosine"]}'))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["update"]:
        sys.exit(0 if data.ensure(force=False) else 1)
    if not data.ready("registries.enriched.json", "graph/item_categories.json"):
        data.ensure()
    if argv[:1] == ["graph"]:
        return graph_main(argv[1:])
    ap = argparse.ArgumentParser(prog="find", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="*")
    ap.add_argument("--brief", help='JSON {"piece": "query", ...} file, or - for stdin')
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--kind", default="", help="component,block,hook,page,template,icon,logo,font,theme,utility")
    ap.add_argument("--registry", default="", help="@a,@b")
    ap.add_argument("--per-registry", type=int, default=2)
    ap.add_argument("--include-demos", action="store_true")
    ap.add_argument("--keyword-only", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.brief:
        concepts = json.load(sys.stdin if a.brief == "-" else open(a.brief))
        concepts = {q: q for q in concepts} if isinstance(concepts, list) else concepts
    else:
        concepts = {q: q for q in a.queries}
    if not concepts:
        ap.print_help(); return
    res = search.search(concepts, [k for k in a.kind.split(",") if k], [r for r in a.registry.split(",") if r],
                        a.k, a.per_registry, a.include_demos, a.keyword_only)
    if a.json: return _dump(res)
    print(search.format_text(res, concepts))


if __name__ == "__main__":
    main()
