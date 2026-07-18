#!/usr/bin/env python3
"""
Re-align Item.embedding in Neo4j to full 3072-d text-embedding-3-large vectors,
so Aura Agent's Similarity Search tool (which embeds queries with 3-large natively)
matches the index. Drops the 1024-d index, recreates at 3072, updates all items.
"""
import os, json, time
import numpy as np
from dotenv import load_dotenv
from neo4j import GraphDatabase
import socket, subprocess, re

load_dotenv()
URI = os.getenv("NEO4J_URI"); USER = os.getenv("NEO4J_USERNAME", "neo4j")
PWD = os.getenv("NEO4J_PASSWORD"); DIM = 3072

# reuse the DNS fallback from load_neo4j
def dns_fallback(uri):
    m = re.search(r"://([^:/]+)", uri or "");  host = m.group(1) if m else None
    if not host: return
    try: socket.getaddrinfo(host, 7687); return
    except socket.gaierror: pass
    for res in ("1.1.1.1", "8.8.8.8"):
        try:
            out = subprocess.run(["nslookup", host, res], capture_output=True, text=True, timeout=8).stdout
            cand = [x for x in re.findall(r"Address:\s*([0-9.]+)", out) if x != res]
            if cand:
                ip = cand[-1]; _o = socket.getaddrinfo
                socket.getaddrinfo = lambda h, *a, **k: _o(ip if h == host else h, *a, **k)
                print(f"  (routing {host} via {ip})"); return
        except Exception: continue

dns_fallback(URI)
items_meta = json.load(open("data/embeddings/items.json"))       # order == items.jsonl
U = np.load("data/embeddings/unique_vectors.npy")                # unique x 3072 (normalized)
ids = [it["id"] for it in items_meta]
vecs = np.stack([U[it["uidx"]] for it in items_meta]).astype(np.float32)
print(f"items: {len(ids)} | vec dim: {vecs.shape[1]}")

drv = GraphDatabase.driver(URI, auth=(USER, PWD)); drv.verify_connectivity()
with drv.session() as s:
    print("dropping old vector index...")
    s.run("DROP INDEX item_embedding IF EXISTS")
    s.run(f"""CREATE VECTOR INDEX item_embedding IF NOT EXISTS FOR (i:Item) ON i.embedding
              OPTIONS {{indexConfig: {{`vector.dimensions`: {DIM},
              `vector.similarity_function`: 'cosine'}}}}""")
    print(f"updating {len(ids)} embeddings to {DIM}-d ...")
    t0 = time.time(); B = 400
    for i in range(0, len(ids), B):
        rows = [{"id": ids[j], "e": vecs[j].tolist()} for j in range(i, min(i+B, len(ids)))]
        s.run("""UNWIND $rows AS r MATCH (n:Item {id:r.id})
                 CALL db.create.setNodeVectorProperty(n, 'embedding', r.e)""", rows=rows)
        if (i // B) % 12 == 0:
            print(f"  {min(i+B,len(ids))}/{len(ids)} ({time.time()-t0:.0f}s)")
    print(f"done in {time.time()-t0:.0f}s")
    d = s.run("""MATCH (i:Item) WHERE i.embedding IS NOT NULL
                 RETURN size(i.embedding) AS dim, count(*) AS n LIMIT 1""").single()
    print(f"verify -> {d['n']} items with {d['dim']}-d embeddings")
drv.close()
