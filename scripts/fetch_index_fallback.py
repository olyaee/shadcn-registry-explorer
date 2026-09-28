#!/usr/bin/env python3
"""Fallback for registries the shadcn MCP could not list (strict schema parse
errors, `{style}` templates, or an index published at a non-template URL).
Fetches candidate registry.json URLs directly and parses leniently.

Candidates per handle: template with {name}=registry (and {style}/ stripped),
the indexUrl we used previously, and <homepage>/registry.json + /r/index.json.
Usage: python scripts/fetch_index_fallback.py [--only @a,@b]
Output: data/raw/mcp_fallback/<handle>.json {handle, ok, indexUrl, items:[{name,type,title,description}]}"""
import json, glob, os, subprocess, sys
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "data/raw/mcp_fallback"
os.makedirs(OUT, exist_ok=True)

idx = {r["name"]: r for r in json.load(open("data/raw/public_registries_index.json"))}
old = {r["handle"]: r for r in json.load(open("data/registries.enriched.json"))["registries"]}
failed = [json.load(open(f))["handle"] for f in glob.glob("data/raw/mcp/*.json")
          if not json.load(open(f))["ok"]]

def fetch(u):
    try:
        out = subprocess.run(["curl", "-sL", "-m", "30", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", u],
                             capture_output=True, text=True).stdout
        body, code = out.rsplit("\n", 1)
        if code != "200":
            return None
        j = json.loads(body)
        items = j.get("items") if isinstance(j, dict) else j
        return items if isinstance(items, list) and items else None
    except Exception:
        return None

only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
for h in sorted(failed):
    if only and h not in only:
        continue
    t = idx[h]["url"]
    # `{style}` registries: the MCP always resolves new-york-v4; current shadcn styles are
    # e.g. radix-nova (Radix variant is usually the superset), then the style-less index.
    cands = [t.replace("{style}", s).replace("{name}", "registry") for s in ("radix-nova", "base-nova")] \
        if "{style}" in t else []
    cands.append(t.replace("{style}/", "").replace("{name}", "registry"))
    if old.get(h, {}).get("components", {}).get("indexUrl"):
        cands.append(old[h]["components"]["indexUrl"])
    base = "{0.scheme}://{0.netloc}".format(urlsplit(idx[h]["homepage"]))
    cands += [f"{base}/registry.json", f"{base}/r/index.json"]
    rec = {"handle": h, "ok": False, "indexUrl": None, "items": []}
    for c in dict.fromkeys(cands):
        items = fetch(c)
        if items:
            rec.update(ok=True, indexUrl=c, items=[
                {"name": i.get("name"), "type": i.get("type", ""), "title": i.get("title", "") or "",
                 "description": (i.get("description") or "").strip()}
                for i in items if isinstance(i, dict) and i.get("name")])
            break
    json.dump(rec, open(f"{OUT}/{h[1:]}.json", "w"), indent=1, ensure_ascii=False)
    print(f"{h:22} {'OK ' + str(len(rec['items'])) + ' ' + rec['indexUrl'] if rec['ok'] else 'no index'}")
