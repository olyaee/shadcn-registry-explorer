#!/usr/bin/env python3
"""
Step 2 crawler: for each of the 238 shadcn community registries, derive its
machine-readable registry index (the authoritative "component list" that powers
`npx shadcn add`), fetch it, and record the items (name/type/description).

Sources:
  - https://ui.shadcn.com/r/registries.json  (handle -> url template)
  - each registry's own registry index JSON (derived from the template)

Output: data/raw/index_probe.json
"""
import json, re, sys, urllib.request, urllib.error, concurrent.futures, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36")

with open("data/raw/registries.json") as f:
    REG = json.load(f)

def host_of(u):
    m = re.match(r'(https?://[^/]+)', u)
    return m.group(1) if m else None

def candidate_index_urls(url_template):
    """Generate ordered candidate index-JSON URLs from an item url template."""
    cands = []
    # 1) substitute placeholders: {name}->registry, {style}->default
    c = url_template.replace('{name}', 'registry')
    c = re.sub(r'\{style\}', 'default', c)
    if not c.endswith('.json'):
        c = c.rstrip('/') + '.json' if not c.endswith('/json') else c
    cands.append(c)
    # 2) directory containing the first placeholder + registry.json
    m = re.match(r'(https?://.*?/)[^/]*\{', url_template)
    if m:
        cands.append(m.group(1) + 'registry.json')
    # 3) host-level common locations
    h = host_of(url_template)
    if h:
        cands.append(h + '/r/registry.json')
        cands.append(h + '/registry.json')
    # dedupe, preserve order
    seen, out = set(), []
    for x in cands:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    return json.loads(raw.decode("utf-8", "replace"))

def slim_items(items):
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name")
        typ = it.get("type", "")
        # skip the style/index meta item that isn't a real component
        if typ == "registry:style":
            continue
        out.append({
            "name": name,
            "type": typ,
            "title": it.get("title") or "",
            "description": it.get("description") or "",
        })
    return out

def probe(entry):
    handle = entry["name"]
    tmpl = entry.get("url", "")
    res = {
        "handle": handle,
        "homepage": entry.get("homepage", ""),
        "urlTemplate": tmpl,
        "indexUrl": None,
        "status": "not_found",
        "itemCount": 0,
        "items": [],
        "error": None,
        "triedCandidates": [],
    }
    for cand in candidate_index_urls(tmpl):
        res["triedCandidates"].append(cand)
        try:
            data = fetch_json(cand)
        except urllib.error.HTTPError as e:
            res["error"] = f"HTTP {e.code} @ {cand}"
            continue
        except Exception as e:
            res["error"] = f"{type(e).__name__}: {str(e)[:80]} @ {cand}"
            continue
        # accept if it looks like a registry index with items
        if isinstance(data, dict) and isinstance(data.get("items"), list) and data["items"]:
            items = slim_items(data["items"])
            if items:
                res.update(indexUrl=cand, status="found", itemCount=len(items),
                           items=items, error=None,
                           registryName=data.get("name"), registryHomepage=data.get("homepage"))
                return res
            else:
                res["error"] = f"index has only meta items @ {cand}"
        else:
            res["error"] = f"json but no items[] @ {cand}"
    return res

def main():
    t0 = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        futs = {ex.submit(probe, e): e["name"] for e in REG}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % 20 == 0:
                print(f"  ...{done}/{len(REG)}  ({time.time()-t0:.0f}s)", file=sys.stderr)
    results.sort(key=lambda r: r["handle"].lower())
    found = [r for r in results if r["status"] == "found"]
    with open("data/raw/index_probe.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nDONE in {time.time()-t0:.0f}s")
    print(f"  total registries : {len(results)}")
    print(f"  index FOUND      : {len(found)}")
    print(f"  index NOT found  : {len(results)-len(found)}")
    print(f"  total components : {sum(r['itemCount'] for r in found)}")

if __name__ == "__main__":
    main()
