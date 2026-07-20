#!/usr/bin/env python3
"""Add each registry's browse-page link(s) to its Registry node in Neo4j
(and into data/graph/registries.json), so the chat can return 'go see it' links."""
import os, json, socket, subprocess, re
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI"); USER = os.getenv("NEO4J_USERNAME", "neo4j"); PWD = os.getenv("NEO4J_PASSWORD")

def dns_fallback(uri):
    m = re.search(r"://([^:/]+)", uri or ""); host = m.group(1) if m else None
    if not host: return
    try: socket.getaddrinfo(host, 7687); return
    except socket.gaierror: pass
    for res in ("1.1.1.1", "8.8.8.8"):
        try:
            out = subprocess.run(["nslookup", host, res], capture_output=True, text=True, timeout=8).stdout
            cand = [x for x in re.findall(r"Address:\s*([0-9.]+)", out) if x != res]
            if cand:
                ip = cand[-1]; _o = socket.getaddrinfo
                socket.getaddrinfo = lambda h, *a, **k: _o(ip if h == host else h, *a, **k); return
        except Exception: continue

pages = json.load(open("data/raw/pages.json"))
rows = []
for handle, links in pages.items():
    if not links: continue
    primary = links[0]
    rows.append({"handle": handle,
                 "browseUrl": primary["url"], "browseLabel": primary["label"],
                 "links": [f'{l["label"]}: {l["url"]}' for l in links]})

# also persist into registries.json
reg = json.load(open("data/graph/registries.json"))
by = {r["handle"]: r for r in reg}
for row in rows:
    if row["handle"] in by:
        by[row["handle"]].update(browseUrl=row["browseUrl"], browseLabel=row["browseLabel"], links=row["links"])
json.dump(reg, open("data/graph/registries.json", "w"), ensure_ascii=False, indent=1)

dns_fallback(URI)
drv = GraphDatabase.driver(URI, auth=(USER, PWD)); drv.verify_connectivity()
with drv.session() as s:
    s.run("""UNWIND $rows AS r MATCH (n:Registry {handle:r.handle})
             SET n.browseUrl=r.browseUrl, n.browseLabel=r.browseLabel, n.links=r.links""", rows=rows)
    c = s.run("MATCH (n:Registry) WHERE n.browseUrl IS NOT NULL RETURN count(*) AS n").single()["n"]
    print(f"updated {len(rows)} rows | Registry nodes with browseUrl: {c}")
    ex = s.run("MATCH (n:Registry {handle:'@aceternity'}) RETURN n.browseUrl AS u, n.links AS l").single()
    print("sample @aceternity ->", ex["u"], "|", ex["l"])
drv.close()
