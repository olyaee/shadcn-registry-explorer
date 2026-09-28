#!/usr/bin/env python3
"""
Fetch or publish the data files listed in data/artifacts.json (GitHub Release assets).

    python scripts/fetch_data.py                                  # download missing / outdated files
    python scripts/fetch_data.py publish --github OWNER/REPO      # after a refresh: new release + manifest
    python scripts/fetch_data.py publish --gdrive PATH=FILE_ID    # or: files you uploaded to Drive yourself

Commit the updated manifest: the MCP package bundles it, so installs fetch these exact bytes.
"""
import argparse, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from shadcn_explorer import data  # noqa: E402

MANIFEST = os.path.join(ROOT, "data", "artifacts.json")
# order = download order: what search + graph need first, the large vectors last
DEFAULT_FILES = ["data/registries.enriched.json", "data/graph/domains.json", "data/graph/categories.json",
                 "data/graph/registries.json", "data/graph/item_categories.json",
                 "data/embeddings/items.json", "data/embeddings/search_vectors_1024.npy"]


def publish(github, gdrive, files):
    m = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"files": []}
    by_path = {f["path"]: f for f in m["files"]}
    paths = files or DEFAULT_FILES
    version = time.strftime("%Y-%m-%d")
    for p in paths:
        full = os.path.join(ROOT, p)
        if not os.path.exists(full):
            sys.exit(f"missing {p} — build it first")
        f = by_path.setdefault(p, {"path": p, "sources": []})
        new = data.sha256(full)
        if f.get("sha256") != new:
            f["sources"] = []                    # old links point at old bytes
        f.update(sha256=new, bytes=os.path.getsize(full))
    if github:
        tag = f"data-{version}"
        assets = [os.path.join(ROOT, p) for p in paths]
        exists = subprocess.run(["gh", "release", "view", tag, "-R", github], capture_output=True).returncode == 0
        subprocess.run(["gh", "release", "upload", tag, *assets, "-R", github, "--clobber"] if exists else
                       ["gh", "release", "create", tag, *assets, "-R", github, "--title", f"Data {version}",
                        "--notes", "Catalogue, graph and search index. Fetched automatically by ./find and the MCP server."],
                       check=True)
        for p in paths:
            by_path[p]["sources"] = [s for s in by_path[p]["sources"] if s["type"] != "github-release"]
            by_path[p]["sources"].insert(0, {"type": "github-release", "repo": github, "tag": tag,
                                             "asset": os.path.basename(p)})
    for spec in gdrive or []:
        p, fid = spec.split("=", 1)
        by_path[p]["sources"] = [s for s in by_path[p]["sources"] if s["type"] != "gdrive"] + [{"type": "gdrive", "id": fid}]
    m.update(version=version, files=[by_path[p] for p in paths])
    json.dump(m, open(MANIFEST, "w"), indent=2)
    for f in m["files"]:
        print(f"  {f['path']}  {f['bytes'] / 1e6:,.1f} MB  {[s['type'] for s in f['sources']] or 'NO SOURCE'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", default="fetch", choices=["fetch", "publish"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--github"); ap.add_argument("--gdrive", nargs="*"); ap.add_argument("--files", nargs="*")
    a = ap.parse_args()
    if a.cmd == "publish":
        publish(a.github, a.gdrive, a.files)
    else:
        sys.exit(0 if data.ensure(force=a.force) else 1)
