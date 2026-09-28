#!/usr/bin/env python3
"""
Download (or publish) the large, git-ignored data files listed in data/artifacts.json.

Teammates, after cloning:
    python scripts/fetch_data.py            # downloads anything missing / out of date, verifies sha256

Maintainers, after refreshing the catalogue or rebuilding the search index:
    python scripts/fetch_data.py publish --github OWNER/REPO     # new GitHub Release + manifest update
    python scripts/fetch_data.py publish --gdrive data/embeddings/search_vectors_1024.npy=<FILE_ID> ...
        (upload the files to Google Drive yourself, share as "Anyone with the link", paste the IDs)
    python scripts/fetch_data.py publish                         # only refresh sha256/size in the manifest

Each file can list several sources; they are tried in order:
    {"type": "github-release", "repo": "owner/name", "tag": "...", "asset": "..."}   (gh CLI, then public URL)
    {"type": "gdrive", "id": "<file id>"}                                           (link-shared file)
    {"type": "url", "url": "https://..."}
Standard library only (plus the `gh` CLI when available).
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "artifacts.json")
DEFAULT_FILES = ["data/registries.enriched.json", "data/embeddings/search_vectors_1024.npy",
                 "data/embeddings/items.json"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stream(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "fetch_data/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        if "text/html" in (r.headers.get("Content-Type") or ""):
            raise RuntimeError("got an HTML page instead of the file (link not shared publicly?)")
        total = int(r.headers.get("Content-Length") or 0)
        done, t0 = 0, time.time()
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r    {done / 1e6:,.0f}/{total / 1e6:,.0f} MB ({time.time() - t0:.0f}s)", end="", flush=True)
        print()


def fetch_source(src, dest):
    t = src["type"]
    if t == "github-release":
        if shutil.which("gh"):
            with tempfile.TemporaryDirectory() as d:
                r = subprocess.run(["gh", "release", "download", src["tag"], "-R", src["repo"],
                                    "-p", src["asset"], "-D", d], capture_output=True, text=True)
                if r.returncode == 0:
                    shutil.move(os.path.join(d, src["asset"]), dest)
                    return
                print(f"    gh: {r.stderr.strip()[:160]} — trying the public URL")
        stream(f'https://github.com/{src["repo"]}/releases/download/{src["tag"]}/{src["asset"]}', dest)
    elif t == "gdrive":
        # this endpoint skips Drive's "can't scan for viruses" interstitial for large files
        stream(f'https://drive.usercontent.google.com/download?id={src["id"]}&export=download&confirm=t', dest)
    elif t == "url":
        stream(src["url"], dest)
    else:
        raise ValueError(f"unknown source type {t}")


def fetch(force):
    if not os.path.exists(MANIFEST):
        sys.exit(f"no manifest at {MANIFEST}")
    m = json.load(open(MANIFEST))
    ok = True
    for f in m["files"]:
        path = os.path.join(ROOT, f["path"])
        if not force and os.path.exists(path) and os.path.getsize(path) == f["bytes"] and sha256(path) == f["sha256"]:
            print(f"✓ {f['path']} (up to date)")
            continue
        if not f.get("sources"):
            print(f"✗ {f['path']}: no download source in the manifest yet — ask the maintainer to publish")
            ok = False
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for src in f["sources"]:
            print(f"↓ {f['path']} via {src['type']}")
            tmp = path + ".part"
            try:
                fetch_source(src, tmp)
                if sha256(tmp) != f["sha256"]:
                    raise RuntimeError("sha256 mismatch")
                os.replace(tmp, path)
                print(f"✓ {f['path']}")
                break
            except Exception as e:
                print(f"    failed: {e}")
                if os.path.exists(tmp):
                    os.remove(tmp)
        else:
            ok = False
    if not ok:
        sys.exit("some files could not be fetched — rebuild locally with: python scripts/embed_items.py")


def publish(github, gdrive, files):
    m = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {"files": []}
    by_path = {f["path"]: f for f in m["files"]}
    paths = files or [f["path"] for f in m["files"]] or DEFAULT_FILES
    version = time.strftime("%Y-%m-%d")
    for p in paths:
        full = os.path.join(ROOT, p)
        if not os.path.exists(full):
            sys.exit(f"missing {p} — build it first")
        f = by_path.setdefault(p, {"path": p, "sources": []})
        new_sha = sha256(full)
        if f.get("sha256") != new_sha:
            f["sources"] = []                    # old links point at old bytes
        f.update(sha256=new_sha, bytes=os.path.getsize(full))
    if github:
        tag = f"data-{version}"
        assets = [os.path.join(ROOT, p) for p in paths]
        r = subprocess.run(["gh", "release", "view", tag, "-R", github], capture_output=True)
        cmd = (["gh", "release", "upload", tag, *assets, "-R", github, "--clobber"] if r.returncode == 0 else
               ["gh", "release", "create", tag, *assets, "-R", github, "--title", f"Data {version}",
                "--notes", "Catalogue + search index. Fetch with `python scripts/fetch_data.py`."])
        subprocess.run(cmd, check=True)
        for p in paths:
            by_path[p]["sources"] = [s for s in by_path[p]["sources"] if s["type"] != "github-release"]
            by_path[p]["sources"].insert(0, {"type": "github-release", "repo": github, "tag": tag,
                                             "asset": os.path.basename(p)})
    for spec in gdrive or []:
        p, fid = spec.split("=", 1)
        if p not in by_path:
            sys.exit(f"--gdrive path {p} is not one of the published files")
        by_path[p]["sources"] = [s for s in by_path[p]["sources"] if s["type"] != "gdrive"]
        by_path[p]["sources"].append({"type": "gdrive", "id": fid})
    m.update(version=version, files=[by_path[p] for p in paths])
    json.dump(m, open(MANIFEST, "w"), indent=2)
    print(f"wrote {os.path.relpath(MANIFEST, ROOT)} — commit it so teammates fetch these exact bytes")
    for f in m["files"]:
        print(f"  {f['path']}  {f['bytes'] / 1e6:,.1f} MB  sources: {[s['type'] for s in f['sources']] or 'NONE'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", default="fetch", choices=["fetch", "publish"])
    ap.add_argument("--force", action="store_true", help="fetch: re-download even if up to date")
    ap.add_argument("--github", help="publish: OWNER/REPO to attach a release to")
    ap.add_argument("--gdrive", nargs="*", help="publish: PATH=FILE_ID pairs for files uploaded to Drive")
    ap.add_argument("--files", nargs="*", help=f"publish: which files (default: manifest or {DEFAULT_FILES})")
    a = ap.parse_args()
    fetch(a.force) if a.cmd == "fetch" else publish(a.github, a.gdrive, a.files)
