#!/usr/bin/env python3
"""
Name the clusters with an LLM (replaces the hand/agent labelling of the first build).

  categories : for each category cluster, show the model its most common item names,
               the enriched per-item categories, kinds and a few descriptions
               -> data/clusters/labels/output_llm.json  [{cluster, label, description}]
  domains    : for each domain, show its categories' labels + sizes
               -> data/clusters/domain_labels.json     {domain: {label, description}}

Run `categories` after scripts/cluster_categories.py, `domains` after scripts/cluster_domains.py.
Usage: python scripts/label_clusters.py categories|domains [--model gpt-6-sol]
"""
import os, sys, json, glob, random, argparse, concurrent.futures, time
from collections import Counter, defaultdict
from dotenv import load_dotenv
from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

CAT_SYSTEM = """You name clusters of shadcn/ui registry items for a component-explorer UI.
Each input cluster lists: the most common item names, the most common per-item category tags,
item kinds, and sample descriptions. Return STRICT JSON {"items":[{"cluster":int,"label":str,"description":str}]}
one per input cluster, same order.
- label: 1-4 words, Title Case, the component TYPE the cluster represents, as a developer would search for it
  ("Pricing Section", "Animated Icon", "Date Picker", "Kanban Board", "Brand Logo"). Plural only when the
  cluster is a family ("Loaders"). No registry names, no marketing words.
- description: ONE plain sentence (<= 110 chars) saying what these items are.
- Sibling clusters may be close; make each label specific enough to tell it apart from the others in the batch
  (e.g. "Line Chart" vs "Bar Chart", not "Chart" twice)."""

DOM_SYSTEM = """You name top-level domains of a shadcn/ui component taxonomy. Each domain lists its categories
with item counts. Return STRICT JSON {"items":[{"domain":int,"label":str,"description":str}]} one per input.
- label: 2-5 words, Title Case, the broad area ("Marketing & Landing Sections", "Forms & Inputs",
  "Icons & Logos"). Labels must be distinct across domains.
- description: ONE sentence listing the main kinds of components inside (<= 140 chars)."""


def chat(client, model, system, payload):
    for attempt in range(8):
        try:
            r = client.chat.completions.create(
                model=model, reasoning_effort="low", response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
            return json.loads(r.choices[0].message.content)["items"]
        except Exception as e:
            if attempt == 7:
                raise
            print(f"  retry {attempt + 1}: {str(e)[:100]}", flush=True)
            time.sleep(min(60, 2 ** attempt))


def categories(client, model):
    cats = json.load(open("data/clusters/categories.json"))
    u2c = {int(k): v for k, v in cats["uidxToCluster"].items()}
    enr = {}
    for r in json.load(open("data/registries.enriched.json"))["registries"]:
        for it in r["components"]["items"]:
            enr[f'{r["handle"]}/{it["name"]}'] = it
    members = defaultdict(list)
    for it in json.load(open("data/embeddings/items.json")):
        members[u2c[it["uidx"]]].append(enr.get(it["id"], {"name": it["name"]}))
    rnd = random.Random(42)
    rows = []
    for c in cats["clusters"]:
        m = members[c["cluster"]]
        descs = [x.get("description") for x in m if x.get("description")]
        rows.append({"cluster": c["cluster"], "size": c["itemCount"],
                     "names": c["sampleNames"][:12],
                     "itemCategories": [k for k, _ in Counter(x.get("category") for x in m if x.get("category")).most_common(6)],
                     "kinds": [k for k, _ in Counter(x.get("kind") for x in m if x.get("kind")).most_common(3)],
                     "descriptions": rnd.sample(descs, min(5, len(descs)))})
    # batch neighbours together (sorted by top item-category) so the model can disambiguate siblings
    rows.sort(key=lambda r: (r["itemCategories"][:1], -r["size"]))
    batches = [rows[i:i + 15] for i in range(0, len(rows), 15)]
    out = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(lambda b: chat(client, model, CAT_SYSTEM, b), batches):
            out += res
    got = {int(o["cluster"]) for o in out}
    print(f"labelled {len(got)}/{len(rows)} categories")
    for fp in glob.glob("data/clusters/labels/*.json"):
        os.remove(fp)                        # previous taxonomy's agent inputs/outputs
    os.makedirs("data/clusters/labels", exist_ok=True)
    json.dump(out, open("data/clusters/labels/output_llm.json", "w"), ensure_ascii=False, indent=1)
    dup = [l for l, n in Counter(o["label"] for o in out).items() if n > 1]
    print(f"duplicate labels ({len(dup)}): {dup[:30]}")


def domains(client, model):
    dom = json.load(open("data/clusters/domains.json"))
    cats = {c["cluster"]: c for c in json.load(open("data/clusters/categories.json"))["clusters"]}
    lab = {int(o["cluster"]): o["label"] for o in json.load(open("data/clusters/labels/output_llm.json"))}
    by_dom = defaultdict(list)
    for cid, d in dom["catToDomain"].items():
        by_dom[d].append((cats[int(cid)]["itemCount"], lab.get(int(cid), cats[int(cid)]["label_guess"])))
    payload = [{"domain": d, "items": sum(n for n, _ in v),
                "categories": [f"{l} ({n})" for n, l in sorted(v, reverse=True)[:40]]}
               for d, v in sorted(by_dom.items())]
    out = chat(client, model, DOM_SYSTEM, payload)
    res = {str(o["domain"]): {"label": o["label"], "description": o["description"]} for o in out}
    json.dump(res, open("data/clusters/domain_labels.json", "w"), ensure_ascii=False, indent=1)
    for p in payload:
        l = res.get(str(p["domain"]), {})
        print(f'D{p["domain"]:<3} {p["items"]:>6}  {l.get("label")}  | {", ".join(p["categories"][:8])}')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["categories", "domains"])
    ap.add_argument("--model", default="gpt-6-sol")
    a = ap.parse_args()
    (categories if a.what == "categories" else domains)(OpenAI(), a.model)
