#!/usr/bin/env python3
"""
Enrich every registry item with a clean description + structured clustering fields
(category, tags, kind, useCases, style) using an LLM in batches.

- Input : data/registries.enriched.json
- Output: data/enrichment/enriched_items.jsonl  (one line per item, resumable)
Then scripts/merge_enrichment.py folds it back into registries.enriched.json.

Usage: python scripts/enrich_descriptions.py [--model gpt-6-sol] [--pending | --all] [--budget-usd 100]
  --pending  only items flagged `needsEnrichment` (new/changed after scripts/update_from_mcp.py)
  (default / --all) every item. Resumable per (id, source text) within the model's output file.
Output: data/enrichment/enriched_items.<model>.jsonl (gpt-4o-mini keeps the legacy enriched_items.jsonl)
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
        # source text from the registry (post-merge `description` is our rewrite)
        "existingDescription": (it.get("descriptionOriginal", it.get("description")) or "")[:300],
    }

# USD per 1M tokens (input, output) — Standard tier, developers.openai.com/api/docs/pricing (2026-09)
PRICES = {"gpt-6-astra": (10.0, 50.0), "gpt-6-sol": (2.0, 10.0), "gpt-6-luna": (0.10, 0.50),
          "gpt-5.6-sol": (4.0, 20.0), "gpt-5.6-terra": (2.0, 12.0), "gpt-5.5": (5.0, 30.0),
          "gpt-5.4": (2.5, 15.0), "gpt-5.4-mini": (0.75, 4.5), "gpt-4o-mini": (0.15, 0.60)}
REASONING = ("gpt-5", "gpt-6", "o3", "o4")   # families that take reasoning_effort, not temperature

def call(client, model, batch, effort, usage):
    payload = [dict(i=k, **b) for k, b in enumerate(batch)]
    kw = {"reasoning_effort": effort} if model.startswith(REASONING) else {"temperature": 0.2}
    for attempt in range(12):
        try:
            resp = client.chat.completions.create(
                model=model, response_format={"type": "json_object"}, **kw,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            )
            usage(resp.usage)
            data = json.loads(resp.choices[0].message.content)
            return data.get("items", [])
        except Exception as e:
            if attempt == 11:
                print(f"  ! batch failed after retries: {e}", flush=True)
                return []  # leave these ids un-done; a re-run picks them up
            time.sleep(min(60, 2 ** attempt))  # rate limits (TPM) need real backoff

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--effort", default="low", help="reasoning_effort for gpt-5+/gpt-6/o-series")
    ap.add_argument("--batch", type=int, default=20)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=None, help="default: data/enrichment/enriched_items.<model>.jsonl")
    ap.add_argument("--pending", action="store_true", help="only items flagged needsEnrichment")
    ap.add_argument("--all", action="store_true", help="every item (re-enrich the whole catalogue)")
    ap.add_argument("--budget-usd", type=float, default=100.0, help="stop submitting batches past this spend")
    args = ap.parse_args()
    args.out = args.out or (OUT if args.model == "gpt-4o-mini" else OUT.replace(".jsonl", f".{args.model}.jsonl"))

    enr = json.load(open("data/registries.enriched.json"))
    work = []
    for r in enr["registries"]:
        if not r["components"]["found"]:
            continue
        for it in r["components"]["items"]:
            if args.pending and not it.get("needsEnrichment"):
                continue
            work.append((f'{r["handle"]}/{it["name"]}', build_input(r, it)))
    if args.limit:
        work = work[:args.limit]

    # done = (id, source text) already written to this output file; a changed source re-enriches
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            try:
                d = json.loads(line)
                if d.get("description"):
                    done.add((d["id"], d.get("src")))
            except Exception: pass
    work = [w for w in work if (w[0], w[1]["existingDescription"]) not in done]
    pin, pout = PRICES.get(args.model, (0, 0))
    print(f"enriching {len(work)} items ({len(done)} already in {args.out}) with {args.model} "
          f"(effort={args.effort}), batch={args.batch}, budget ${args.budget_usd:.0f}", flush=True)

    client = OpenAI()
    batches = [work[i:i+args.batch] for i in range(0, len(work), args.batch)]
    fout = open(args.out, "a")
    t0 = time.time(); n = 0
    lock = __import__("threading").Lock()
    tok = {"in": 0, "out": 0}
    cost = lambda: (tok["in"] * pin + tok["out"] * pout) / 1e6
    def usage(u):
        with lock:
            tok["in"] += u.prompt_tokens; tok["out"] += u.completion_tokens
    def run(batch):
        nonlocal n
        if cost() >= args.budget_usd:
            return
        inputs = [b[1] for b in batch]
        res = call(client, args.model, inputs, args.effort, usage)
        if not res:
            return
        by_i = {r.get("i"): r for r in res if isinstance(r, dict)}
        lines = []
        for k, (iid, inp) in enumerate(batch):
            r = by_i.get(k, {})
            if not r.get("description"):
                continue          # missing from the response: stays un-done for a re-run
            lines.append(json.dumps({
                "id": iid, "name": inp["name"], "src": inp["existingDescription"], "model": args.model,
                "description": r.get("description", ""), "category": r.get("category", ""),
                "tags": r.get("tags", []), "kind": r.get("kind", ""),
                "useCases": r.get("useCases", []), "style": r.get("style", []),
            }, ensure_ascii=False))
        with lock:
            if lines:
                fout.write("\n".join(lines) + "\n"); fout.flush()
            n += len(batch)
            if n % 1000 < args.batch:
                print(f"  {n}/{len(work)}  ({time.time()-t0:.0f}s)  tokens in={tok['in']:,} out={tok['out']:,}  "
                      f"~${cost():.2f}", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(run, batches))
    fout.close()
    print(f"done {n} items in {time.time()-t0:.0f}s -> {args.out} | tokens in={tok['in']:,} "
          f"out={tok['out']:,} | ~${cost():.2f}" + ("  (BUDGET REACHED)" if cost() >= args.budget_usd else ""), flush=True)

if __name__ == "__main__":
    main()
