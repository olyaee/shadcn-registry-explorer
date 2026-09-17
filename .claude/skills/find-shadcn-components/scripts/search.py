#!/usr/bin/env python3
"""Score the local shadcn registry catalogue against a UI brief.

Edit GROUPS to your mechanics, then run:
    python3 .claude/skills/find-shadcn-components/scripts/search.py [--limit N] [--type ui,component]

Prints matches ranked by keyword hits across name+title+description, with the
`@handle/name` install id for each. Read descriptions — rank is a hint, not truth.
"""
import argparse
import json
import os
import sys

# --- Edit this per brief. concept -> keywords (substring match, lowercased). ---
GROUPS = {
    "slider":        ["slider", "thumb", "track fill"],
    "stepped/notch": ["step dot", "stepped", "notch", "tick", "detent", "snap", "discrete", "increment"],
    "dot-matrix":    ["dot matrix", "dot-matrix", "pixel", "grid of dots", "dot grid", "halftone", "led", "matrix"],
    "shimmer":       ["shimmer", "twinkle", "sparkle", "glow", "glimmer", "pulse", "flicker", "aurora"],
    "morph-label":   ["morph", "text swap", "rotating text", "flip text", "crossfade", "number flow", "animated number", "text transition"],
    "gauge/meter":   ["gauge", "meter", "intensity", "level", "effort", "temperature"],
    "motion":        ["spring", "motion", "gesture", "physics", "inertia"],
}

DATA = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data",
                    "registries.enriched.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--type", default="", help="comma list to keep, e.g. ui,component")
    ap.add_argument("--data", default=os.path.abspath(DATA))
    args = ap.parse_args()

    keep_types = {t.strip() for t in args.type.split(",") if t.strip()}
    with open(args.data) as fh:
        regs = json.load(fh)["registries"]

    rows = []
    for r in regs:
        for it in (r.get("components") or {}).get("items") or []:
            typ = (it.get("type") or "").replace("registry:", "")
            if keep_types and typ not in keep_types:
                continue
            text = " ".join([it.get("name") or "", it.get("title") or "",
                             it.get("description") or ""]).lower()
            hits = {g: [k for k in kws if k in text] for g, kws in GROUPS.items()}
            hits = {g: v for g, v in hits.items() if v}
            if not hits:
                continue
            score = sum(len(v) for v in hits.values()) + 2 * len(hits)
            rows.append((score, r["handle"], it.get("name"), typ,
                         (it.get("description") or "")[:130], list(hits)))

    rows.sort(key=lambda x: -x[0])
    print(f"{len(rows)} matches (showing {min(args.limit, len(rows))})\n")
    for score, handle, name, typ, desc, groups in rows[: args.limit]:
        print(f"[{score:>2}] npx shadcn add {handle}/{name}  ({typ})  {groups}")
        print(f"     {desc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
