"""Download the catalogue, graph and search index listed in the manifest (GitHub Release assets)."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from . import paths


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _stream(url, dest, log):
    req = urllib.request.Request(url, headers={"User-Agent": "shadcn-explorer"})
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        if "text/html" in (r.headers.get("Content-Type") or ""):
            raise RuntimeError("got an HTML page instead of the file (link not shared publicly?)")
        total, done, t0 = int(r.headers.get("Content-Length") or 0), 0, time.time()
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            if total and log:
                print(f"\r    {done / 1e6:,.0f}/{total / 1e6:,.0f} MB ({time.time() - t0:.0f}s)",
                      end="", flush=True, file=sys.stderr)
        if log:
            print(file=sys.stderr)


def _fetch_source(src, dest, log):
    if src["type"] == "github-release":
        url = f'https://github.com/{src["repo"]}/releases/download/{src["tag"]}/{src["asset"]}'
        try:
            return _stream(url, dest, log)
        except Exception:
            if not shutil.which("gh"):                # private repo: fall back to an authed download
                raise
            with tempfile.TemporaryDirectory() as d:
                subprocess.run(["gh", "release", "download", src["tag"], "-R", src["repo"],
                                "-p", src["asset"], "-D", d], check=True, capture_output=True)
                shutil.move(os.path.join(d, src["asset"]), dest)
    elif src["type"] == "gdrive":
        _stream(f'https://drive.usercontent.google.com/download?id={src["id"]}&export=download&confirm=t', dest, log)
    elif src["type"] == "url":
        _stream(src["url"], dest, log)
    else:
        raise ValueError(f'unknown source type {src["type"]}')


def ensure(only=None, force=False, log=True):
    """Download files missing or out of date. `only`: substrings selecting manifest paths. Returns True if all ok."""
    m = json.load(open(paths.manifest()))
    ok = True
    for f in m["files"]:
        if only and not any(o in f["path"] for o in only):
            continue
        dest = paths.root() / f["path"]
        if not force and dest.exists() and dest.stat().st_size == f["bytes"] and sha256(dest) == f["sha256"]:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        for src in f.get("sources", []):
            if log:
                print(f"↓ {f['path']} ({f['bytes'] / 1e6:,.0f} MB)", file=sys.stderr)
            tmp = dest.with_name(dest.name + ".part")
            try:
                _fetch_source(src, tmp, log)
                if sha256(tmp) != f["sha256"]:
                    raise RuntimeError("sha256 mismatch")
                os.replace(tmp, dest)
                break
            except Exception as e:
                if log:
                    print(f"    failed via {src['type']}: {e}", file=sys.stderr)
                tmp.unlink(missing_ok=True)
        else:
            ok = False
    return ok


def ready(*names):
    """True when every named data file (relative to data/) exists."""
    return all(paths.data(n).exists() for n in names)
