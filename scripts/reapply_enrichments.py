#!/usr/bin/env python3
"""Re-apply the data-quality enrichments after a fresh graph reload:
Item.viewUrl (verified), Registry.browseUrl/links, Registry.active (dead flags),
and fix @ramonclaudio-coderabbit homepage. Also folds viewUrl into items.jsonl."""
import os, json, socket, subprocess, re
from dotenv import load_dotenv
from neo4j import GraphDatabase
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
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
                ip=cand[-1];_o=socket.getaddrinfo
                socket.getaddrinfo=lambda h,*a,**k:_o(ip if h==host else h,*a,**k); return
        except Exception: continue

# --- item view URLs (verified) ---
kept=json.load(open("data/quality/item_urls_verified.json"))
# fold into items.jsonl for reproducibility
items=[json.loads(l) for l in open("data/graph/items.jsonl")]
with open("data/graph/items.jsonl","w") as f:
    for it in items:
        if it["id"] in kept: it["viewUrl"]=kept[it["id"]]
        f.write(json.dumps(it,ensure_ascii=False)+"\n")

# --- browse links ---
pages=json.load(open("data/raw/pages.json"))
link_rows=[]
for h,links in pages.items():
    if not links: continue
    link_rows.append({"handle":h,"browseUrl":links[0]["url"],"browseLabel":links[0]["label"],
                      "links":[f'{l["label"]}: {l["url"]}' for l in links]})

DEAD={"@commercn","@icons-animated","@pureui","@wandry-ui"}
FIX_HOME={"@ramonclaudio-coderabbit":"https://ramonclaudio.com/"}

dns_fallback(URI)
drv=GraphDatabase.driver(URI,auth=(USER,PWD)); drv.verify_connectivity()
with drv.session() as s:
    s.run("UNWIND $rows AS r MATCH (n:Item {id:r.id}) SET n.viewUrl=r.u",
          rows=[{"id":k,"u":v} for k,v in kept.items()])
    s.run("""UNWIND $rows AS r MATCH (n:Registry {handle:r.handle})
             SET n.browseUrl=r.browseUrl, n.browseLabel=r.browseLabel, n.links=r.links""", rows=link_rows)
    s.run("MATCH (n:Registry) SET n.active=true")
    s.run("UNWIND $d AS h MATCH (n:Registry {handle:h}) SET n.active=false", d=list(DEAD))
    for h,u in FIX_HOME.items():
        s.run("MATCH (n:Registry {handle:$h}) SET n.homepage=$u", h=h, u=u)
    c=s.run("""MATCH (i:Item) WHERE i.viewUrl IS NOT NULL WITH count(i) AS vurl
               MATCH (r:Registry) WHERE r.browseUrl IS NOT NULL WITH vurl, count(r) AS burl
               MATCH (r2:Registry {active:false}) RETURN vurl, burl, count(r2) AS dead""").single()
    print(f"re-applied -> Item.viewUrl={c['vurl']} | Registry.browseUrl={c['burl']} | inactive={c['dead']}")
drv.close()
