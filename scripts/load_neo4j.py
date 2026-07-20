#!/usr/bin/env python3
"""
Load the knowledge graph into Neo4j (Aura).

Reads NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD from .env.
Creates constraints + a cosine vector index on Item.embedding (1024-d), then loads
Domain/Category/Registry/Item nodes and the hierarchy + provenance relationships.

Usage:
  python scripts/load_neo4j.py --check      # test connection only
  python scripts/load_neo4j.py              # full load
  python scripts/load_neo4j.py --wipe       # clear graph first, then load
"""
import os, json, sys, time, argparse, socket, subprocess, re
import numpy as np
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI"); USER = os.getenv("NEO4J_USERNAME", "neo4j")
PWD = os.getenv("NEO4J_PASSWORD"); DIM = 3072

def install_dns_fallback(uri):
    """If the local resolver can't resolve the Aura host (router DNS-rebind
    protection), resolve it via public DNS and patch socket.getaddrinfo.
    TLS SNI/cert validation still uses the real hostname, so this stays secure."""
    m = re.search(r"://([^:/]+)", uri or "")
    if not m:
        return
    host = m.group(1)
    try:
        socket.getaddrinfo(host, 7687)
        return  # local DNS is fine
    except socket.gaierror:
        pass
    ip = None
    for resolver in ("1.1.1.1", "8.8.8.8"):
        try:
            out = subprocess.run(["nslookup", host, resolver], capture_output=True,
                                 text=True, timeout=8).stdout
            cand = [x for x in re.findall(r"Address:\s*([0-9.]+)", out) if x != resolver]
            if cand:
                ip = cand[-1]; break
        except Exception:
            continue
    if not ip:
        return
    print(f"  (local DNS can't resolve {host}; routing via public-DNS IP {ip})")
    _orig = socket.getaddrinfo
    def patched(h, *a, **k):
        return _orig(ip if h == host else h, *a, **k)
    socket.getaddrinfo = patched

def need_creds():
    if not URI or not PWD or "<your-instance>" in (URI or ""):
        sys.exit("NEO4J_URI / NEO4J_PASSWORD not set in .env — add your Aura credentials first.")

def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--wipe", action="store_true")
    args = ap.parse_args()
    need_creds()
    install_dns_fallback(URI)

    drv = GraphDatabase.driver(URI, auth=(USER, PWD))
    drv.verify_connectivity()
    print(f"connected to {URI}")
    if args.check:
        with drv.session() as s:
            v = s.run("CALL dbms.components() YIELD versions RETURN versions[0] AS v").single()["v"]
        print(f"Neo4j version {v} — connection OK.")
        drv.close(); return

    domains = json.load(open("data/graph/domains.json"))
    categories = json.load(open("data/graph/categories.json"))
    registries = json.load(open("data/graph/registries.json"))
    items = [json.loads(l) for l in open("data/graph/items.jsonl")]
    vecs = np.load("data/graph/item_vectors.npy")
    assert len(items) == len(vecs)

    with drv.session() as s:
        if args.wipe:
            print("wiping existing graph...")
            s.run("MATCH (n) CALL {WITH n DETACH DELETE n} IN TRANSACTIONS OF 10000 ROWS")

        print("schema: constraints + vector index...")
        for lbl, key in [("Domain", "id"), ("Category", "id"), ("Registry", "handle"), ("Item", "id")]:
            s.run(f"CREATE CONSTRAINT {lbl.lower()}_key IF NOT EXISTS "
                  f"FOR (n:{lbl}) REQUIRE n.{key} IS UNIQUE")
        s.run(f"""CREATE VECTOR INDEX item_embedding IF NOT EXISTS
                  FOR (i:Item) ON i.embedding
                  OPTIONS {{indexConfig: {{`vector.dimensions`: {DIM},
                  `vector.similarity_function`: 'cosine'}}}}""")

        s.run("MERGE (r:Root {id:'root'}) SET r.label='All Registries'")

        print(f"loading {len(domains)} domains...")
        s.run("""UNWIND $rows AS d MERGE (n:Domain {id:d.id})
                 SET n.label=d.label, n.description=d.description, n.itemCount=d.itemCount
                 WITH n MATCH (r:Root {id:'root'}) MERGE (r)-[:HAS_DOMAIN]->(n)""", rows=domains)

        print(f"loading {len(categories)} categories...")
        s.run("""UNWIND $rows AS c MERGE (n:Category {id:c.id})
                 SET n.label=c.label, n.description=c.description, n.itemCount=c.itemCount
                 WITH n, c MATCH (d:Domain {id:c.domainId}) MERGE (d)-[:HAS_CATEGORY]->(n)""",
              rows=categories)

        print(f"loading {len(registries)} registries...")
        s.run("""UNWIND $rows AS r MERGE (n:Registry {handle:r.handle})
                 SET n.name=r.name, n.homepage=r.homepage, n.terminology=r.terminology,
                     n.componentCount=r.componentCount, n.hasComponents=r.hasComponents""",
              rows=registries)

        print(f"loading {len(items)} items (with embeddings)...")
        t0 = time.time(); done = 0
        BATCH = 500
        rows_all = [{**it, "embedding": vecs[i].tolist()} for i, it in enumerate(items)]
        for chunk in batched(rows_all, BATCH):
            s.run("""UNWIND $rows AS it
                     MERGE (n:Item {id:it.id})
                     SET n.name=it.name, n.type=it.type, n.description=it.description,
                         n.handle=it.handle, n.kind=it.kind, n.tags=it.tags,
                         n.useCases=it.useCases
                     WITH n, it
                     CALL db.create.setNodeVectorProperty(n, 'embedding', it.embedding)
                     WITH n, it MATCH (c:Category {id:it.categoryId}) MERGE (c)-[:HAS_ITEM]->(n)
                     WITH n, it MATCH (r:Registry {handle:it.handle}) MERGE (n)-[:PROVIDED_BY]->(r)
                  """, rows=chunk)
            done += len(chunk)
            if done % 5000 < BATCH:
                print(f"  {done}/{len(items)} ({time.time()-t0:.0f}s)")
        print(f"items loaded in {time.time()-t0:.0f}s")

        counts = s.run("""MATCH (d:Domain) WITH count(d) AS domains
                          MATCH (c:Category) WITH domains, count(c) AS cats
                          MATCH (r:Registry) WITH domains, cats, count(r) AS regs
                          MATCH (i:Item) RETURN domains, cats, regs, count(i) AS items""").single()
        print(f"\nLOADED -> domains={counts['domains']} categories={counts['cats']} "
              f"registries={counts['regs']} items={counts['items']}")
    drv.close()

if __name__ == "__main__":
    main()
