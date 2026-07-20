# Data-Quality Pass — Links & Enrichment

## 1. Browse links (each registry's components/blocks page)
- Checked: **362** links across 227 registries
- Working (200, not redirect-to-home, not soft-404): **360**
- Broken found & **fixed: 2** — @pulkitxm (soft-404 → /components), @ramonclaudio-coderabbit (404 → homepage)

## 2. Registry homepages
- Checked: **238**
- Live: **234** (incl. @elevenlabs-ui & @motion-primitives which returned HTTP 429 rate-limits — confirmed alive)
- Confirmed dead → **flagged `active=false`: 4** — @commercn, @icons-animated, @pureui, @wandry-ui
- Fixed: @ramonclaudio-coderabbit homepage → working root

## 3. Per-item "view this component" URLs (NEW enrichment)
- URL pattern detected for **93 registries**; **9481** candidate URLs generated
- **Every candidate individually verified** (200 + not soft-404 + page actually shows the item)
- **Kept: 5754** exact deep links · **rejected 3727 false positives** (SPA soft-200s / timeouts)
- ~15% of all 37,814 items now deep-link to the exact component page; the rest fall back to the registry browse page

## Where it lives (all pushed to Neo4j + files)
- `Item.viewUrl` — verified exact component page (5,754 items)
- `Registry.browseUrl` / `Registry.links` — component/blocks gallery (227)
- `Registry.active` — false for 4 dead registries
- Files: data/graph/items.jsonl, data/graph/registries.json, data/quality/*.json
