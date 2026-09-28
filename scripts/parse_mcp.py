#!/usr/bin/env python3
"""Parse raw shadcn-MCP `list_items_in_registries` text (data/raw/mcp/<handle>.json)
into structured items. Line format emitted by the MCP (shadcn/dist, formatter `_`):
    - <name> (<type>) - <description> [<@registry>]
      Add command: `...`
type / description are optional. Items are separated by a blank line.
Returns {handle: {"ok", "error", "total", "items": [{name,type,description}]}}."""
import json, glob, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEM_RE = re.compile(
    r"^- (?P<name>\S+)(?: \((?P<type>[^)\s]+)\))?(?: - (?P<desc>.*?))? \[(?P<reg>@[^\]\s]+)\]\s*\n\s+Add command:",
    re.S | re.M)

def parse_text(text):
    body = text.split("\n\n", 2)
    # items start after the "Showing items" header
    start = text.find("\n- ")
    chunks = re.split(r"\n\n(?=- )", text[start + 1:]) if start >= 0 else []
    items = []
    for ch in chunks:
        m = ITEM_RE.match(ch)
        if m:
            items.append({"name": m["name"], "type": m["type"] or "",
                          "description": (m["desc"] or "").strip()})
    return items

def load_all():
    out = {}
    for fp in sorted(glob.glob(os.path.join(ROOT, "data/raw/mcp/*.json"))):
        r = json.load(open(fp))
        rec = {"ok": r["ok"], "error": r["error"], "total": r["total"],
               "fetchedAt": r["fetchedAt"], "items": []}
        if r["ok"]:
            rec["items"] = parse_text(r["rawText"])
        out[r["handle"]] = rec
    return out

if __name__ == "__main__":
    data = load_all()
    bad = {h: (len(v["items"]), v["total"]) for h, v in data.items() if v["ok"] and len(v["items"]) != v["total"]}
    print(f"ok={sum(v['ok'] for v in data.values())} items={sum(len(v['items']) for v in data.values())} parse-mismatch={bad}")
