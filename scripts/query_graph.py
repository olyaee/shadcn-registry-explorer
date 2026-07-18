#!/usr/bin/env python3
"""Verify / demo the knowledge graph.
  python scripts/query_graph.py --stats
  python scripts/query_graph.py --category Button
  python scripts/query_graph.py --search "glowing gradient border button"
"""
import os, argparse, re, socket, subprocess
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()
from importlib import import_module
import_module("scripts.load_neo4j") if False else None
# reuse the DNS fallback from the loader
import sys; sys.path.insert(0, "scripts")
from load_neo4j import install_dns_fallback
URI=os.getenv("NEO4J_URI"); USER=os.getenv("NEO4J_USERNAME","neo4j"); PWD=os.getenv("NEO4J_PASSWORD")
install_dns_fallback(URI)
drv=GraphDatabase.driver(URI, auth=(USER,PWD))

def stats():
    with drv.session() as s:
        for lbl in ["Domain","Category","Registry","Item"]:
            n=s.run(f"MATCH (n:{lbl}) RETURN count(n) AS c").single()["c"]
            print(f"  {lbl:<10} {n}")
        print("\nTop domains by item count:")
        for r in s.run("""MATCH (d:Domain)-[:HAS_CATEGORY]->(:Category)-[:HAS_ITEM]->(i:Item)
                          RETURN d.label AS d, count(i) AS n ORDER BY n DESC LIMIT 8"""):
            print(f"   {r['n']:>6}  {r['d']}")

def category(label):
    with drv.session() as s:
        print(f"'{label}' components across registries:")
        for r in s.run("""MATCH (d:Domain)-[:HAS_CATEGORY]->(c:Category)-[:HAS_ITEM]->(i:Item)-[:PROVIDED_BY]->(reg:Registry)
                          WHERE toLower(c.label)=toLower($l)
                          RETURN reg.handle AS reg, i.name AS name, i.description AS desc
                          ORDER BY reg LIMIT 20""", l=label):
            print(f"   {r['reg']:<18} {r['name']:<26} {(r['desc'] or '')[:46]}")

def search(text, k=12):
    vec=OpenAI().embeddings.create(model="text-embedding-3-large", input=[text],
                                   dimensions=1024).data[0].embedding
    with drv.session() as s:
        print(f"vector search: '{text}'")
        for r in s.run("""CALL db.index.vector.queryNodes('item_embedding', $k, $v)
                          YIELD node, score
                          MATCH (node)-[:PROVIDED_BY]->(reg:Registry)
                          OPTIONAL MATCH (c:Category)-[:HAS_ITEM]->(node)
                          RETURN score, node.name AS name, reg.handle AS reg,
                                 c.label AS cat, node.description AS desc""", k=k, v=vec):
            print(f"   {r['score']:.3f} {r['reg']:<16} {r['name']:<24} [{r['cat']}] {(r['desc'] or '')[:40]}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--stats",action="store_true")
    ap.add_argument("--category")
    ap.add_argument("--search")
    a=ap.parse_args()
    if a.stats: stats()
    if a.category: category(a.category)
    if a.search: search(a.search)
    drv.close()
