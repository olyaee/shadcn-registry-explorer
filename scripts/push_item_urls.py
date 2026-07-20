#!/usr/bin/env python3
"""Push verified per-item view URLs onto Item nodes in Neo4j (Item.viewUrl)."""
import os, json, socket, subprocess, re
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv()
URI=os.getenv("NEO4J_URI"); USER=os.getenv("NEO4J_USERNAME","neo4j"); PWD=os.getenv("NEO4J_PASSWORD")

def dns_fallback(uri):
    m=re.search(r"://([^:/]+)",uri or ""); host=m.group(1) if m else None
    if not host: return
    try: socket.getaddrinfo(host,7687); return
    except socket.gaierror: pass
    for res in ("1.1.1.1","8.8.8.8"):
        try:
            out=subprocess.run(["nslookup",host,res],capture_output=True,text=True,timeout=8).stdout
            cand=[x for x in re.findall(r"Address:\s*([0-9.]+)",out) if x!=res]
            if cand:
                ip=cand[-1]; _o=socket.getaddrinfo
                socket.getaddrinfo=lambda h,*a,**k:_o(ip if h==host else h,*a,**k); return
        except Exception: continue

kept=json.load(open("data/quality/item_urls_verified.json"))
rows=[{"id":k,"u":v} for k,v in kept.items()]
dns_fallback(URI)
drv=GraphDatabase.driver(URI,auth=(USER,PWD)); drv.verify_connectivity()
with drv.session() as s:
    for i in range(0,len(rows),1000):
        s.run("UNWIND $rows AS r MATCH (n:Item {id:r.id}) SET n.viewUrl=r.u", rows=rows[i:i+1000])
    c=s.run("MATCH (i:Item) WHERE i.viewUrl IS NOT NULL RETURN count(*) AS n").single()["n"]
    print(f"set viewUrl on {c} Item nodes (from {len(rows)} verified URLs)")
drv.close()
