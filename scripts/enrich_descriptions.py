#!/usr/bin/env python3
"""
Enrich every registry item with a clean description + structured clustering fields
(category, tags, kind, useCases, style) using an LLM in batches.

- Input : data/registries.enriched.json
- Output: data/enrichment/enriched_items.jsonl  (one line per item, resumable)
Then scripts/merge_enrichment.py folds it back into registries.enriched.json.

Usage: python scripts/enrich_descriptions.py [--limit N] [--model gpt-4o-mini] [--batch 20]
"""
import os, json, sys, time, argparse, concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OUT = "data/enrichment/enriched_items.jsonl"

SYSTEM = """You enrich metadata for shadcn/ui registry items powering a semantic search + clustering system.
For each item you get: the registry (name + description), the item's name, its registry type, and any existing description.
Return factual, CONSISTENT, concise metadata. Infer from the item NAME and registry context. Do NOT invent specific
visual details you cannot reasonably infer — stay general when unsure. Never use marketing fluff.

Return STRICT JSON: {"items":[{...}]} with one object per input item, in order, each with:
- "i": the input index (integer)
- "description": ONE sentence, <=160 chars, factual, starts capitalized. Describe the thing DIRECTLY with an
  article ("An animated downward-arrow icon.", "A button with a shining background effect."). Do NOT restate the
  raw item name or write "X is a ..." (bad: "Btn Bg Shine is a button"; good: "A button with an animated shine sweep").
- "category": the normalized canonical kind as a short kebab-case noun that GROUPS this with equivalents across
  registries. Examples: "button","accordion","dialog","hero-section","auth-form","pricing-section","bar-chart",
  "data-table","brand-logo","animated-icon","carousel","navbar","dropdown-menu","toast","use-hook". Be consistent:
  every sign-in/login block -> "auth-form"; every logo -> "brand-logo"; every animated icon -> "animated-icon".
- "tags": 3-7 lowercase keyword strings (function + visual + tech), e.g. ["animated","gradient","cta","motion"].
- "kind": one of component | block | hook | page | template | icon | logo | font | theme | utility.
- "useCases": 0-3 of: marketing, dashboard, auth, e-commerce, data-display, navigation, forms, media, ai, content, developer.
- "style": 0-3 short visual descriptors (e.g. "animated","3d","brutalist","glassmorphic","minimal","retro","gradient"). [] if none.
"""

def build_input(reg, it):
    return {
        "registry": reg["name"],
        "registryDescription": (reg.get("description") or "")[:200],
        "terminology": reg["components"].get("terminology"),
        "name": it["name"],
        "type": it.get("type", ""),
        "existingDescription": (it.get("description") or "")[:300],
    }

def call(client, model, batch):
    payload = [dict(i=k, **b) for k, b in enumerate(batch)]
    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=model, temperature=0.2,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            )
            data = json.loads(resp.choices[0].message.content)
            return data.get("items", [])
        except Exception as e:
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    enr = json.load(open("data/registries.enriched.json"))
    work = []
    for r in enr["registries"]:
        if not r["components"]["found"]:
            continue
        for it in r["components"]["items"]:
            work.append((f'{r["handle"]}/{it["name"]}', build_input(r, it)))
    if args.limit:
        work = work[:args.limit]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            try: done.add(json.loads(line)["id"])
            except Exception: pass
    work = [w for w in work if w[0] not in done]
    print(f"enriching {len(work)} items ({len(done)} already done) with {args.model}, batch={args.batch}")

    client = OpenAI()
    batches = [work[i:i+args.batch] for i in range(0, len(work), args.batch)]
    fout = open(args.out, "a")
    t0 = time.time(); n = 0
    lock = __import__("threading").Lock()
    def run(batch):
        nonlocal n
        ids = [b[0] for b in batch]
        inputs = [b[1] for b in batch]
        res = call(client, args.model, inputs)
        by_i = {r.get("i"): r for r in res if isinstance(r, dict)}
        lines = []
        for k, (iid, inp) in enumerate(batch):
            r = by_i.get(k, {})
            lines.append(json.dumps({
                "id": iid, "name": inp["name"],
                "description": r.get("description", ""), "category": r.get("category", ""),
                "tags": r.get("tags", []), "kind": r.get("kind", ""),
                "useCases": r.get("useCases", []), "style": r.get("style", []),
            }, ensure_ascii=False))
        with lock:
            fout.write("\n".join(lines) + "\n"); fout.flush()
            n += len(batch)
            if n % 200 < args.batch:
                print(f"  {n}/{len(work)}  ({time.time()-t0:.0f}s)", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, batches))
    fout.close()
    print(f"done {n} items in {time.time()-t0:.0f}s -> {args.out}")

if __name__ == "__main__":
    main()
