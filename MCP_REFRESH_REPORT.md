# Registry refresh via the shadcn MCP

- **Refreshed:** 2026-09-28 from `https://ui.shadcn.com/r/registries.json`
- **Method:** shadcn MCP (npx shadcn mcp · list_items_in_registries) with direct-index fallback
- **Registries:** 394 (156 new since the 2026-07-18 capture) · with components: 380
- **Total items:** 76,162
- **Sources:** MCP 340 · direct index fallback 20 · stale (kept from previous capture) 29 · unresolved new 4 · mirror 1
- **Item changes in refreshed registries:** +38,705 added · −358 removed · 2,662 source descriptions changed · 535 renamed · 30,736 unchanged

Items that are new or whose source description changed are re-enriched by `scripts/enrich_descriptions.py --pending` + `scripts/merge_enrichment.py --pending`. New items have `linkMethod: "pending"` until the deep-link stage is re-run.

## Refreshed registries

| Registry | Source | Before | After | + | − | Desc changed |
|---|---|---:|---:|---:|---:|---:|
| `@keyline` 🆕 | shadcn-mcp | 0 | 9736 | 9736 | 0 | 0 |
| `@hugeicons-animated-vue` 🆕 | shadcn-mcp | 0 | 6122 | 6122 | 0 | 0 |
| `@catalogs` 🆕 | shadcn-mcp | 0 | 2910 | 2910 | 0 | 0 |
| `@cnippet` 🆕 | shadcn-mcp | 0 | 1132 | 1132 | 0 | 0 |
| `@spaceui` 🆕 | shadcn-mcp | 0 | 1100 | 1100 | 0 | 0 |
| `@beste-ui` | shadcn-mcp | 1516 | 2189 | 673 | 0 | 6 |
| `@atomloader` 🆕 | shadcn-mcp | 0 | 591 | 591 | 0 | 0 |
| `@herocn` 🆕 | shadcn-mcp | 0 | 555 | 555 | 0 | 0 |
| `@ns-ui` 🆕 | shadcn-mcp | 0 | 542 | 542 | 0 | 0 |
| `@tailark` | shadcn-mcp | 210 | 476 | 403 | 136 | 73 |
| `@shadcn-dashboard` 🆕 | shadcn-mcp | 0 | 508 | 508 | 0 | 0 |
| `@uiable` | shadcn-mcp | 550 | 986 | 451 | 15 | 535 |
| `@shadcnblocks` | shadcn-mcp | 3730 | 4171 | 441 | 0 | 528 |
| `@canvas-ui` 🆕 | shadcn-mcp | 0 | 420 | 420 | 0 | 0 |
| `@ai2` 🆕 | shadcn-mcp | 0 | 414 | 414 | 0 | 0 |
| `@lema-ds` 🆕 | shadcn-mcp | 0 | 378 | 378 | 0 | 0 |
| `@emailcn` 🆕 | shadcn-mcp | 0 | 338 | 338 | 0 | 0 |
| `@flagcn` 🆕 | shadcn-mcp | 0 | 321 | 321 | 0 | 0 |
| `@dashboardblocks` 🆕 | shadcn-mcp | 0 | 305 | 305 | 0 | 0 |
| `@seamui` 🆕 | shadcn-mcp | 0 | 305 | 305 | 0 | 0 |
| `@react-bits` | shadcn-mcp | 556 | 844 | 288 | 0 | 0 |
| `@shadcncraft` | shadcn-mcp | 22 | 300 | 278 | 0 | 0 |
| `@reui` | shadcn-mcp | 1534 | 1805 | 271 | 0 | 9 |
| `@preskok` 🆕 | shadcn-mcp | 0 | 260 | 260 | 0 | 0 |
| `@designali` 🆕 | shadcn-mcp | 0 | 253 | 253 | 0 | 0 |
| `@initium` 🆕 | shadcn-mcp | 0 | 252 | 252 | 0 | 0 |
| `@remotionui` 🆕 | registry-index-direct | 0 | 235 | 235 | 0 | 0 |
| `@mischief` 🆕 | shadcn-mcp | 0 | 234 | 234 | 0 | 0 |
| `@reactframe` 🆕 | shadcn-mcp | 0 | 230 | 230 | 0 | 0 |
| `@shadcn-space` | shadcn-mcp | 736 | 941 | 206 | 1 | 3 |
| `@shadcnuikit` | shadcn-mcp | 759 | 958 | 203 | 0 | 237 |
| `@spectrumui` | shadcn-mcp | 116 | 315 | 200 | 0 | 0 |
| `@ilinxa` 🆕 | shadcn-mcp | 0 | 184 | 184 | 0 | 0 |
| `@evilcharts` | shadcn-mcp | 129 | 279 | 166 | 16 | 0 |
| `@000h-cojeev` 🆕 | shadcn-mcp | 0 | 174 | 174 | 0 | 0 |
| `@craftui` 🆕 | shadcn-mcp | 0 | 170 | 170 | 0 | 0 |
| `@amicro` 🆕 | shadcn-mcp | 0 | 169 | 169 | 0 | 0 |
| `@hugeicons-animated` 🆕 | shadcn-mcp | 0 | 165 | 165 | 0 | 0 |
| `@motion-lexicon` 🆕 | shadcn-mcp | 0 | 150 | 150 | 0 | 0 |
| `@localmode` 🆕 | shadcn-mcp | 0 | 147 | 147 | 0 | 0 |
| `@hirael` | shadcn-mcp | 147 | 278 | 132 | 1 | 71 |
| `@blockforge` 🆕 | registry-index-direct | 0 | 131 | 131 | 0 | 0 |
| `@retab` 🆕 | shadcn-mcp | 0 | 130 | 130 | 0 | 0 |
| `@uiception` 🆕 | shadcn-mcp | 0 | 124 | 124 | 0 | 0 |
| `@diarmuradi` 🆕 | shadcn-mcp | 0 | 119 | 119 | 0 | 0 |
| `@assistant-ui` | shadcn-mcp | 40 | 156 | 116 | 0 | 40 |
| `@yukihi` 🆕 | shadcn-mcp | 0 | 113 | 113 | 0 | 0 |
| `@corsair-ui` 🆕 | shadcn-mcp | 0 | 109 | 109 | 0 | 0 |
| `@delta` | shadcn-mcp | 91 | 20 | 18 | 89 | 2 |
| `@persianlabsui` 🆕 | shadcn-mcp | 0 | 105 | 105 | 0 | 0 |
| `@blode` 🆕 | shadcn-mcp | 0 | 100 | 100 | 0 | 0 |
| `@motiq` 🆕 | shadcn-mcp | 0 | 100 | 100 | 0 | 0 |
| `@remocn` | shadcn-mcp | 236 | 332 | 98 | 2 | 0 |
| `@moduix-react` 🆕 | shadcn-mcp | 0 | 96 | 96 | 0 | 0 |
| `@shadcnstore` | shadcn-mcp | 182 | 274 | 92 | 0 | 100 |
| `@nostalgia-ui` 🆕 | shadcn-mcp | 0 | 91 | 91 | 0 | 0 |
| `@smoothui` | shadcn-mcp | 158 | 246 | 88 | 0 | 1 |
| `@atroui` 🆕 | shadcn-mcp | 0 | 84 | 84 | 0 | 0 |
| `@honestui` 🆕 | shadcn-mcp | 0 | 84 | 84 | 0 | 0 |
| `@soralabs` | shadcn-mcp | 74 | 68 | 39 | 45 | 0 |
| `@usva` 🆕 | shadcn-mcp | 0 | 83 | 83 | 0 | 0 |
| `@tween-ui` 🆕 | shadcn-mcp | 0 | 82 | 82 | 0 | 0 |
| `@pantoken` 🆕 | shadcn-mcp | 0 | 80 | 80 | 0 | 0 |
| `@ssych` 🆕 | shadcn-mcp | 0 | 80 | 80 | 0 | 0 |
| `@kobra` 🆕 | shadcn-mcp | 0 | 78 | 78 | 0 | 0 |
| `@oidc` 🆕 | shadcn-mcp | 0 | 78 | 78 | 0 | 0 |
| `@neon-ui` 🆕 | shadcn-mcp | 0 | 77 | 77 | 0 | 0 |
| `@ark-cn` 🆕 | shadcn-mcp | 0 | 76 | 76 | 0 | 0 |
| `@7ovr` | shadcn-mcp | 173 | 248 | 75 | 0 | 173 |
| `@rescript-shadcn` | shadcn-mcp | 460 | 535 | 75 | 0 | 0 |
| `@vue-bits` | shadcn-mcp | 132 | 197 | 70 | 5 | 0 |
| `@bjork-ui` 🆕 | shadcn-mcp | 0 | 74 | 74 | 0 | 0 |
| `@1st-pouf` 🆕 | shadcn-mcp | 0 | 71 | 71 | 0 | 0 |
| `@tile-ui` 🆕 | shadcn-mcp | 0 | 71 | 71 | 0 | 0 |
| `@pulld` | shadcn-mcp | 31 | 99 | 68 | 0 | 31 |
| `@scrimui` 🆕 | shadcn-mcp | 0 | 68 | 68 | 0 | 0 |
| `@corecn` 🆕 | shadcn-mcp | 0 | 67 | 67 | 0 | 0 |
| `@sevenui` 🆕 | shadcn-mcp | 0 | 67 | 67 | 0 | 0 |
| `@afterglow` 🆕 | shadcn-mcp | 0 | 66 | 66 | 0 | 0 |
| `@aicanvas` | shadcn-mcp | 117 | 183 | 66 | 0 | 117 |
| `@materialcn` 🆕 | shadcn-mcp | 0 | 66 | 66 | 0 | 0 |
| `@vectorstudio-ir` 🆕 | shadcn-mcp | 0 | 66 | 66 | 0 | 0 |
| `@navui` 🆕 | shadcn-mcp | 0 | 62 | 62 | 0 | 0 |
| `@whiskeyjack` 🆕 | shadcn-mcp | 0 | 62 | 62 | 0 | 0 |
| `@tweenly` 🆕 | shadcn-mcp | 0 | 61 | 61 | 0 | 0 |
| `@gridcn` 🆕 | shadcn-mcp | 0 | 60 | 60 | 0 | 0 |
| `@brut-ui` 🆕 | shadcn-mcp | 0 | 59 | 59 | 0 | 0 |
| `@quill` 🆕 | shadcn-mcp | 0 | 59 | 59 | 0 | 0 |
| `@washiveil` 🆕 | shadcn-mcp | 0 | 58 | 58 | 0 | 0 |
| `@beui` | shadcn-mcp | 71 | 127 | 56 | 0 | 7 |
| `@iandefined` 🆕 | shadcn-mcp | 0 | 56 | 56 | 0 | 0 |
| `@starseam` 🆕 | shadcn-mcp | 0 | 56 | 56 | 0 | 0 |
| `@tuiparts` 🆕 | shadcn-mcp | 0 | 56 | 56 | 0 | 0 |
| `@better-auth-ui` 🆕 | shadcn-mcp | 0 | 54 | 54 | 0 | 0 |
| `@dashboardcn` 🆕 | shadcn-mcp | 0 | 54 | 54 | 0 | 0 |
| `@interior` 🆕 | shadcn-mcp | 0 | 54 | 54 | 0 | 0 |
| `@saastro` 🆕 | shadcn-mcp | 0 | 53 | 53 | 0 | 0 |
| `@uniquel` 🆕 | shadcn-mcp | 0 | 52 | 52 | 0 | 0 |
| `@atelier` 🆕 | shadcn-mcp | 0 | 51 | 51 | 0 | 0 |
| `@easeui` 🆕 | shadcn-mcp | 0 | 50 | 50 | 0 | 0 |
| `@microkit` 🆕 | shadcn-mcp | 0 | 49 | 49 | 0 | 0 |
| `@plotcn` 🆕 | shadcn-mcp | 0 | 49 | 49 | 0 | 0 |
| `@react-aria` | shadcn-mcp | 109 | 158 | 49 | 0 | 0 |
| `@aniui` | registry-index-direct | 118 | 166 | 48 | 0 | 6 |
| `@buzzform` 🆕 | shadcn-mcp | 0 | 48 | 48 | 0 | 0 |
| `@velobits` 🆕 | shadcn-mcp | 0 | 48 | 48 | 0 | 0 |
| `@sf-fleet-hud` 🆕 | shadcn-mcp | 0 | 47 | 47 | 0 | 0 |
| `@snapcn` 🆕 | shadcn-mcp | 0 | 47 | 47 | 0 | 0 |
| `@shadcn-ui-blocks` | shadcn-mcp | 3962 | 4007 | 45 | 0 | 0 |
| `@ericts` | shadcn-mcp | 28 | 56 | 36 | 8 | 1 |
| `@sc1m` 🆕 | shadcn-mcp | 0 | 43 | 43 | 0 | 0 |
| `@uselayouts` | shadcn-mcp | 26 | 64 | 40 | 2 | 0 |
| `@livedocs` 🆕 | shadcn-mcp | 0 | 41 | 41 | 0 | 0 |
| `@brainless` 🆕 | shadcn-mcp | 0 | 40 | 40 | 0 | 0 |
| `@d2` 🆕 | shadcn-mcp | 0 | 40 | 40 | 0 | 0 |
| `@opaline` 🆕 | shadcn-mcp | 0 | 40 | 40 | 0 | 0 |
| `@liquefy-ui` 🆕 | shadcn-mcp | 0 | 39 | 39 | 0 | 0 |
| `@rawkitui` 🆕 | shadcn-mcp | 0 | 39 | 39 | 0 | 0 |
| `@fluent2-react-kit` 🆕 | shadcn-mcp | 0 | 37 | 37 | 0 | 0 |
| `@svelte-bits` | shadcn-mcp | 128 | 164 | 36 | 0 | 0 |
| `@intentui` | shadcn-mcp | 557 | 592 | 35 | 0 | 0 |
| `@hexui` 🆕 | shadcn-mcp | 0 | 34 | 34 | 0 | 0 |
| `@niko-table` 🆕 | shadcn-mcp | 0 | 34 | 34 | 0 | 0 |
| `@componentry` | shadcn-mcp | 55 | 56 | 17 | 16 | 0 |
| `@sona-ui` | shadcn-mcp | 16 | 46 | 31 | 1 | 8 |
| `@zippystarter` | shadcn-mcp | 45 | 77 | 32 | 0 | 0 |
| `@avertra-ui` 🆕 | shadcn-mcp | 0 | 31 | 31 | 0 | 0 |
| `@efferd` | shadcn-mcp | 200 | 231 | 31 | 0 | 0 |
| `@formscn` 🆕 | shadcn-mcp | 0 | 30 | 30 | 0 | 0 |
| `@paceui-gsap` 🆕 | shadcn-mcp | 0 | 29 | 29 | 0 | 0 |
| `@wa-ui` 🆕 | shadcn-mcp | 0 | 29 | 29 | 0 | 0 |
| `@23rd` 🆕 | shadcn-mcp | 0 | 28 | 28 | 0 | 0 |
| `@lucide-animated` | shadcn-mcp | 440 | 467 | 28 | 0 | 0 |
| `@uicapsule` | shadcn-mcp | 29 | 52 | 25 | 2 | 27 |
| `@skecher-ui` 🆕 | shadcn-mcp | 0 | 26 | 26 | 0 | 0 |
| `@slidecn` 🆕 | shadcn-mcp | 0 | 26 | 26 | 0 | 0 |
| `@cligentic` 🆕 | shadcn-mcp | 0 | 24 | 24 | 0 | 0 |
| `@payload-components` | shadcn-mcp | 58 | 82 | 24 | 0 | 0 |
| `@nekode` 🆕 | shadcn-mcp | 0 | 23 | 23 | 0 | 0 |
| `@aceternity` | shadcn-mcp | 270 | 291 | 22 | 0 | 1 |
| `@indiacn` | shadcn-mcp | 26 | 48 | 22 | 0 | 0 |
| `@agentui` 🆕 | shadcn-mcp | 0 | 21 | 21 | 0 | 0 |
| `@fluid` | shadcn-mcp | 52 | 71 | 20 | 1 | 19 |
| `@pipecat` 🆕 | shadcn-mcp | 0 | 21 | 21 | 0 | 0 |
| `@wensity` | registry-index-direct | 70 | 91 | 21 | 0 | 67 |
| `@morphiq` 🆕 | shadcn-mcp | 0 | 20 | 20 | 0 | 0 |
| `@systaliko-ui` | shadcn-mcp | 154 | 172 | 20 | 0 | 1 |
| `@knock-codes` 🆕 | shadcn-mcp | 0 | 19 | 19 | 0 | 0 |
| `@amarjay-ui` 🆕 | shadcn-mcp | 0 | 18 | 18 | 0 | 0 |
| `@crafterui` 🆕 | shadcn-mcp | 0 | 18 | 18 | 0 | 0 |
| `@motokoui` 🆕 | shadcn-mcp | 0 | 18 | 18 | 0 | 0 |
| `@onchain-ui` 🆕 | shadcn-mcp | 0 | 18 | 18 | 0 | 0 |
| `@spark-ui` 🆕 | shadcn-mcp | 0 | 18 | 18 | 0 | 0 |
| `@stylexui` 🆕 | shadcn-mcp | 0 | 18 | 18 | 0 | 0 |
| `@akoder` 🆕 | shadcn-mcp | 0 | 17 | 17 | 0 | 0 |
| `@commercn` | shadcn-mcp | 0 | 17 | 17 | 0 | 0 |
| `@ncdai` | shadcn-mcp | 52 | 69 | 17 | 0 | 0 |
| `@starck` 🆕 | shadcn-mcp | 0 | 16 | 16 | 0 | 0 |
| `@data-table-filters` 🆕 | shadcn-mcp | 0 | 15 | 15 | 0 | 0 |
| `@knot-ui` 🆕 | shadcn-mcp | 0 | 15 | 15 | 0 | 0 |
| `@pane` 🆕 | shadcn-mcp | 0 | 15 | 15 | 0 | 0 |
| `@quiz-ui` 🆕 | shadcn-mcp | 0 | 15 | 15 | 0 | 0 |
| `@termcn` | shadcn-mcp | 329 | 344 | 15 | 0 | 0 |
| `@coss` | shadcn-mcp | 565 | 579 | 14 | 0 | 1 |
| `@moumenlab` 🆕 | shadcn-mcp | 0 | 14 | 14 | 0 | 0 |
| `@toggles` 🆕 | shadcn-mcp | 0 | 14 | 14 | 0 | 0 |
| `@agentblog` 🆕 | shadcn-mcp | 0 | 13 | 13 | 0 | 0 |
| `@evex` | shadcn-mcp | 11 | 23 | 12 | 0 | 1 |
| `@extend` | shadcn-mcp | 55 | 67 | 12 | 0 | 1 |
| `@dgit` 🆕 | shadcn-mcp | 0 | 11 | 11 | 0 | 0 |
| `@ecomcn` 🆕 | shadcn-mcp | 0 | 11 | 11 | 0 | 0 |
| `@fibo` 🆕 | shadcn-mcp | 0 | 11 | 11 | 0 | 0 |
| `@flightcn` | shadcn-mcp | 2 | 13 | 11 | 0 | 1 |
| `@flx` | shadcn-mcp | 441 | 450 | 10 | 1 | 0 |
| `@kokonutui` | shadcn-mcp | 40 | 51 | 11 | 0 | 40 |
| `@sekei` 🆕 | shadcn-mcp | 0 | 11 | 11 | 0 | 0 |
| `@tetra-ui` | shadcn-mcp | 36 | 45 | 10 | 1 | 0 |
| `@unlumen-ui` | shadcn-mcp | 224 | 235 | 11 | 0 | 2 |
| `@axicharts` 🆕 | shadcn-mcp | 0 | 10 | 10 | 0 | 0 |
| `@flowui` 🆕 | shadcn-mcp | 0 | 10 | 10 | 0 | 0 |
| `@mewo` 🆕 | shadcn-mcp | 0 | 10 | 10 | 0 | 0 |
| `@ui-shrushank` 🆕 | shadcn-mcp | 0 | 8 | 8 | 0 | 0 |
| `@evilbuttons` | registry-index-direct | 29 | 28 | 3 | 4 | 14 |
| `@shadcn-studio` | shadcn-mcp | 687 | 694 | 7 | 0 | 0 |
| `@supabase` | shadcn-mcp | 60 | 67 | 7 | 0 | 0 |
| `@8starlabs-ui` | shadcn-mcp | 70 | 76 | 6 | 0 | 0 |
| `@aevr` | shadcn-mcp | 0 | 6 | 6 | 0 | 0 |
| `@bits-ui` 🆕 | shadcn-mcp | 0 | 6 | 6 | 0 | 0 |
| `@blobatar` 🆕 | shadcn-mcp | 0 | 6 | 6 | 0 | 0 |
| `@forgeui` | shadcn-mcp | 28 | 24 | 1 | 5 | 6 |
| `@ratneshc` 🆕 | shadcn-mcp | 0 | 6 | 6 | 0 | 0 |
| `@simple-ai` 🆕 | shadcn-mcp | 0 | 6 | 6 | 0 | 0 |
| `@awwwardedui` 🆕 | shadcn-mcp | 0 | 5 | 5 | 0 | 0 |
| `@blocks-so` | shadcn-mcp | 77 | 81 | 5 | 0 | 0 |
| `@boldkit` | shadcn-mcp | 91 | 96 | 5 | 0 | 0 |
| `@svgl` | shadcn-mcp | 665 | 662 | 5 | 0 | 0 |
| `@thegridcn` | shadcn-mcp | 140 | 144 | 5 | 0 | 0 |
| `@vernostudio` 🆕 | shadcn-mcp | 0 | 5 | 5 | 0 | 0 |
| `@waves-cn` | shadcn-mcp | 7 | 12 | 5 | 0 | 0 |
| `@abui` | shadcn-mcp | 16 | 20 | 4 | 0 | 0 |
| `@diceui` | registry-index-direct | 242 | 246 | 4 | 0 | 0 |
| `@iconiq` | shadcn-mcp | 116 | 120 | 4 | 0 | 0 |
| `@magicui` | shadcn-mcp | 246 | 250 | 4 | 0 | 0 |
| `@mediadrop` 🆕 | shadcn-mcp | 0 | 4 | 4 | 0 | 0 |
| `@styleui` 🆕 | shadcn-mcp | 0 | 4 | 4 | 0 | 0 |
| `@voraui` 🆕 | shadcn-mcp | 0 | 4 | 4 | 0 | 0 |
| `@wxcn` 🆕 | shadcn-mcp | 0 | 4 | 4 | 0 | 0 |
| `@8bitcn` | shadcn-mcp | 118 | 121 | 3 | 0 | 0 |
| `@amplo` | shadcn-mcp | 6 | 9 | 3 | 0 | 4 |
| `@cubby-ui` | shadcn-mcp | 80 | 79 | 1 | 2 | 0 |
| `@diklein` 🆕 | shadcn-mcp | 0 | 3 | 3 | 0 | 0 |
| `@elsecase` 🆕 | shadcn-mcp | 0 | 3 | 3 | 0 | 0 |
| `@gaia` | shadcn-mcp | 26 | 29 | 3 | 0 | 0 |
| `@gammaui` | shadcn-mcp | 60 | 63 | 3 | 0 | 0 |
| `@plate` | shadcn-mcp | 321 | 324 | 3 | 0 | 0 |
| `@channel3` | shadcn-mcp | 25 | 23 | 0 | 2 | 1 |
| `@einui` | shadcn-mcp | 42 | 44 | 2 | 0 | 1 |
| `@elevenlabs-ui` | registry-index-direct | 48 | 50 | 2 | 0 | 0 |
| `@gc-solid` | shadcn-mcp | 59 | 61 | 2 | 0 | 0 |
| `@grootstudio` | shadcn-mcp | 24 | 26 | 2 | 0 | 0 |
| `@gymnopedies` | shadcn-mcp | 47 | 49 | 2 | 0 | 0 |
| `@layish` 🆕 | shadcn-mcp | 0 | 2 | 2 | 0 | 0 |
| `@limeplay` | shadcn-mcp | 50 | 52 | 2 | 0 | 0 |
| `@loading-ui` | shadcn-mcp | 48 | 50 | 2 | 0 | 0 |
| `@roiui` | shadcn-mcp | 124 | 121 | 0 | 2 | 1 |
| `@shadcnui-blocks` | shadcn-mcp | 542 | 542 | 1 | 1 | 6 |
| `@tablecn` 🆕 | shadcn-mcp | 0 | 2 | 2 | 0 | 0 |
| `@taki` | shadcn-mcp | 538 | 540 | 2 | 0 | 0 |
| `@agents-ui` | shadcn-mcp | 17 | 18 | 1 | 0 | 0 |
| `@amap` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@animate-ui` | shadcn-mcp | 579 | 580 | 1 | 0 | 0 |
| `@benday` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@corr` | shadcn-mcp | 59 | 60 | 1 | 0 | 0 |
| `@dominik-ui` | shadcn-mcp | 3 | 4 | 1 | 0 | 0 |
| `@eldoraui` | shadcn-mcp | 114 | 115 | 1 | 0 | 0 |
| `@elements` | shadcn-mcp | 359 | 360 | 1 | 0 | 0 |
| `@emstein-ui` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@glasscn` | shadcn-mcp | 64 | 65 | 1 | 0 | 0 |
| `@jolyui` | shadcn-mcp | 198 | 199 | 1 | 0 | 0 |
| `@joyco` | shadcn-mcp | 47 | 48 | 1 | 0 | 0 |
| `@kibo-ui` | shadcn-mcp | 40 | 41 | 1 | 0 | 0 |
| `@kinetic` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@mapcn` | shadcn-mcp | 8 | 9 | 1 | 0 | 0 |
| `@nuqs` | shadcn-mcp | 5 | 6 | 1 | 0 | 0 |
| `@odysseyui` | shadcn-mcp | 287 | 288 | 1 | 0 | 0 |
| `@openmirai` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@pacekit` | shadcn-mcp | 22 | 23 | 1 | 0 | 0 |
| `@paceui` | shadcn-mcp | 22 | 23 | 1 | 0 | 0 |
| `@prosekit` | shadcn-mcp | 548 | 549 | 1 | 0 | 0 |
| `@sans` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@shadcnloaders` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@shivraj-roy` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@threecn` | shadcn-mcp | 27 | 28 | 1 | 0 | 0 |
| `@trophy-ui` | shadcn-mcp | 17 | 18 | 1 | 0 | 0 |
| `@zenoadmin` 🆕 | shadcn-mcp | 0 | 1 | 1 | 0 | 0 |
| `@abstract` | registry-index-direct | 13 | 13 | 0 | 0 | 0 |
| `@agentcn` | shadcn-mcp | 76 | 76 | 0 | 0 | 0 |
| `@ai-elements` | shadcn-mcp | 136 | 136 | 0 | 0 | 0 |
| `@algolia` | shadcn-mcp | 5 | 5 | 0 | 0 | 0 |
| `@animbits` | shadcn-mcp | 99 | 99 | 0 | 0 | 0 |
| `@approvals-ui` | shadcn-mcp | 6 | 6 | 0 | 0 | 0 |
| `@arc` | shadcn-mcp | 2 | 2 | 0 | 0 | 0 |
| `@asanshay` | shadcn-mcp | 27 | 27 | 0 | 0 | 0 |
| `@auth0` | shadcn-mcp | 6 | 6 | 0 | 0 | 0 |
| `@baraile-loader` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@basecn` | shadcn-mcp | 56 | 56 | 0 | 0 | 0 |
| `@baselayer` | shadcn-mcp | 26 | 26 | 0 | 0 | 0 |
| `@better-upload` | shadcn-mcp | 4 | 4 | 0 | 0 | 0 |
| `@billingsdk` | shadcn-mcp | 35 | 35 | 0 | 0 | 0 |
| `@bklit` | shadcn-mcp | 56 | 56 | 0 | 0 | 0 |
| `@bundui` | shadcn-mcp | 217 | 217 | 0 | 0 | 0 |
| `@cardcn` | shadcn-mcp | 27 | 27 | 0 | 0 | 0 |
| `@chamaac` | shadcn-mcp | 90 | 90 | 0 | 0 | 0 |
| `@clerk` | shadcn-mcp | 12 | 12 | 0 | 0 | 0 |
| `@cognicatch` | shadcn-mcp | 4 | 4 | 0 | 0 | 0 |
| `@contentbit` | shadcn-mcp | 20 | 20 | 0 | 0 | 0 |
| `@cult-ui` | registry-index-direct | 157 | 157 | 0 | 0 | 0 |
| `@delego` | shadcn-mcp | 6 | 6 | 0 | 0 | 0 |
| `@dotmatrix` | shadcn-mcp | 91 | 91 | 0 | 0 | 0 |
| `@dsikeres1` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@exabase` | shadcn-mcp | 61 | 61 | 0 | 0 | 0 |
| `@fab-ui` | shadcn-mcp | 44 | 44 | 0 | 0 | 0 |
| `@flowkit-ui` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@formcn` | shadcn-mcp | 9 | 9 | 0 | 0 | 0 |
| `@framecn` | shadcn-mcp | 101 | 101 | 0 | 0 | 0 |
| `@gamekitui` | shadcn-mcp | 12 | 12 | 0 | 0 | 0 |
| `@gamifykit` | shadcn-mcp | 3 | 3 | 0 | 0 | 0 |
| `@glass-ui` | shadcn-mcp | 49 | 49 | 0 | 0 | 0 |
| `@gooseui` | shadcn-mcp | 19 | 19 | 0 | 0 | 0 |
| `@gpt-vis` | shadcn-mcp | 27 | 27 | 0 | 0 | 0 |
| `@grainly-icons` | registry-index-direct | 23 | 23 | 0 | 0 | 0 |
| `@ha-components` | shadcn-mcp | 12 | 12 | 0 | 0 | 0 |
| `@headcodecms` | registry-index-direct | 1 | 1 | 0 | 0 | 0 |
| `@heatmap` | registry-index-direct | 4 | 4 | 0 | 0 | 0 |
| `@heroicons-animated` | shadcn-mcp | 316 | 316 | 0 | 0 | 0 |
| `@inferencesh` | shadcn-mcp | 14 | 14 | 0 | 0 | 0 |
| `@kanpeki` | shadcn-mcp | 260 | 259 | 0 | 0 | 0 |
| `@kapwa` | shadcn-mcp | 11 | 11 | 0 | 0 | 0 |
| `@kaui` | shadcn-mcp | 10 | 10 | 0 | 0 | 0 |
| `@launchui` | registry-index-direct | 24 | 24 | 0 | 0 | 0 |
| `@lens-blocks` | shadcn-mcp | 24 | 24 | 0 | 0 | 0 |
| `@lmscn` | shadcn-mcp | 10 | 10 | 0 | 0 | 0 |
| `@lumiui` | shadcn-mcp | 67 | 67 | 0 | 0 | 0 |
| `@lytenyte` | shadcn-mcp | 2 | 2 | 0 | 0 | 0 |
| `@manifest` | shadcn-mcp | 32 | 32 | 0 | 0 | 0 |
| `@mksingh` | shadcn-mcp | 36 | 36 | 0 | 0 | 0 |
| `@motion-primitives` | shadcn-mcp | 33 | 33 | 0 | 0 | 0 |
| `@mozaika` | shadcn-mcp | 548 | 548 | 0 | 0 | 518 |
| `@mui-treasury` | shadcn-mcp | 192 | 192 | 0 | 0 | 0 |
| `@nexus-labs` | registry-index-direct | 86 | 86 | 0 | 0 | 0 |
| `@nexus-ui` | shadcn-mcp | 15 | 15 | 0 | 0 | 0 |
| `@nteract` | shadcn-mcp | 35 | 35 | 0 | 0 | 0 |
| `@nusaiba` | shadcn-mcp | 119 | 119 | 0 | 0 | 0 |
| `@ogimagecn` | shadcn-mcp | 22 | 22 | 0 | 0 | 0 |
| `@openstatus` | shadcn-mcp | 26 | 26 | 0 | 0 | 0 |
| `@optics` | shadcn-mcp | 79 | 79 | 0 | 0 | 0 |
| `@oui` | shadcn-mcp | 137 | 137 | 0 | 0 | 0 |
| `@paddle` | shadcn-mcp | 14 | 14 | 0 | 0 | 0 |
| `@paletteui` | shadcn-mcp | 65 | 65 | 0 | 0 | 0 |
| `@pastecn` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@paykit-sdk` | shadcn-mcp | 21 | 21 | 0 | 0 | 0 |
| `@pixelact-ui` | shadcn-mcp | 28 | 28 | 0 | 0 | 0 |
| `@prompt-kit` | shadcn-mcp | 23 | 23 | 0 | 0 | 0 |
| `@ramonclaudio-coderabbit` | shadcn-mcp | 19 | 19 | 0 | 0 | 0 |
| `@react-easy-modals` | registry-index-direct | 2 | 2 | 0 | 0 | 0 |
| `@react-slot` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@retroui` | shadcn-mcp | 54 | 54 | 0 | 0 | 0 |
| `@saaskit` | registry-index-direct | 10 | 10 | 0 | 0 | 0 |
| `@satoriui` | shadcn-mcp | 15 | 15 | 0 | 0 | 0 |
| `@scrollxui` | shadcn-mcp | 180 | 180 | 0 | 0 | 1 |
| `@shadcn-editor` | shadcn-mcp | 1 | 1 | 0 | 0 | 1 |
| `@shadcn-map` | shadcn-mcp | 32 | 32 | 0 | 0 | 0 |
| `@shadcndesign` | shadcn-mcp | 44 | 44 | 0 | 0 | 0 |
| `@shadcnhooks` | shadcn-mcp | 58 | 58 | 0 | 0 | 0 |
| `@shadcnmaps` | shadcn-mcp | 361 | 361 | 0 | 0 | 0 |
| `@skiper-ui` | shadcn-mcp | 37 | 37 | 0 | 0 | 0 |
| `@slide-cn` | shadcn-mcp | 20 | 20 | 0 | 0 | 0 |
| `@solaceui` | shadcn-mcp | 39 | 39 | 0 | 0 | 0 |
| `@soundcn` | shadcn-mcp | 816 | 816 | 0 | 0 | 0 |
| `@spell` | shadcn-mcp | 33 | 33 | 0 | 0 | 0 |
| `@stepper` | shadcn-mcp | 3 | 3 | 0 | 0 | 0 |
| `@tailgrids` | shadcn-mcp | 61 | 61 | 0 | 0 | 0 |
| `@tailwind-admin` | shadcn-mcp | 102 | 102 | 0 | 0 | 0 |
| `@tailwind-builder` | registry-index-direct | 4 | 4 | 0 | 0 | 0 |
| `@terrae` | shadcn-mcp | 40 | 40 | 0 | 0 | 0 |
| `@text-ui` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@toc-cn` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@tokenui` | shadcn-mcp | 17 | 17 | 0 | 0 | 0 |
| `@tool-ui` | shadcn-mcp | 27 | 27 | 0 | 0 | 0 |
| `@tour` | shadcn-mcp | 1 | 1 | 0 | 0 | 0 |
| `@turbopills-ui` | shadcn-mcp | 10 | 10 | 0 | 0 | 0 |
| `@typedora-ui` | shadcn-mcp | 4 | 4 | 0 | 0 | 0 |
| `@ui-layouts` | shadcn-mcp | 327 | 327 | 0 | 0 | 0 |
| `@uitripled` | registry-index-direct | 282 | 282 | 0 | 0 | 0 |
| `@utilcn` | shadcn-mcp | 17 | 17 | 0 | 0 | 0 |
| `@uui` | registry-index-direct | 6 | 6 | 0 | 0 | 0 |
| `@vllnt-ui` | shadcn-mcp | 313 | 313 | 0 | 0 | 0 |
| `@wds` | shadcn-mcp | 10 | 10 | 0 | 0 | 0 |
| `@wigggle-ui` | shadcn-mcp | 119 | 119 | 0 | 0 | 0 |
| `@xcn` | registry-index-direct | 6 | 6 | 0 | 0 | 0 |

## Not refreshed

| Registry | In directory | Health | Items kept | Why |
|---|---|---|---:|---|
| `@ai-blocks` | yes | unavailable | 127 | Error (NOT_FOUND): The item at https://webllm.org/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@aliimam` | no | — | 0 | delisted from directory |
| `@blockus` | yes | degraded | 500 | Error: Unexpected token '<', "<!DOCTYPE "... is not valid JSON |
| `@creative-tim` | yes | unavailable | 471 | Error (FETCH_ERROR): Failed to fetch from registry (400): https://www.creative-tim.com/ui/r/registry.json?limit=0 |
| `@darx` | yes | unavailable | 1 | Error: Request to https://darshitdev.in/r/registry.json?limit=0 failed, reason: getaddrinfo ENOTFOUND darshitdev.in |
| `@devl` | yes | unavailable | 158 | Error (FETCH_ERROR): Failed to fetch from registry (500): https://devl.dev/r/registry.json?limit=0 |
| `@doras-ui` | yes | unavailable | 4 | Error (FETCH_ERROR): Failed to fetch from registry (500): https://ui.doras.to/r/registry.json?limit=0 |
| `@emerald-ui` | yes | unavailable | 28 | Error (NOT_FOUND): The item at https://emerald-ui.com/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@fonttrio` | yes | unavailable | 2305 | Error (NOT_FOUND): The item at https://www.fonttrio.xyz/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@hextaui` | yes | unavailable | 139 | Error (NOT_FOUND): The item at https://hextaui.com/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@icons-animated` | yes | unavailable | 0 | Error (NOT_FOUND): The item at https://icons.lndev.me/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@jalco` | yes | unavailable | 36 | Error (NOT_FOUND): The item at https://ui.justinlevine.me/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@moleculeui` | yes | unavailable | 0 | Error: Request to https://www.moleculeui.design/r/registry.json?limit=0 failed, reason: getaddrinfo ENOTFOUND www.moleculeui.design |
| `@motion-menu` | yes | unavailable | 0 | Error (NOT_FOUND): The item at https://motion-menu-two.vercel.app/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@n3wth` | yes | observing | 0 | Error: Unexpected token '<', "<!doctype "... is not valid JSON |
| `@neobrutalism` | yes | unavailable | 44 | Error (NOT_FOUND): The item at https://www.neobrutalism.dev/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@nessra-ui` | yes | unavailable | 62 | Error (NOT_FOUND): The item at https://nessra-ui.vercel.app/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@nexus-elements` | yes | unavailable | 7 | Error (NOT_FOUND): The item at https://elements.nexus.availproject.org/r/registry.json?limit=0 was not found. It may not exist at the regist |
| `@nordaun` | yes | unavailable | 8 | Error: Request to https://ui.nordaun.com/r/registry.json?limit=0 failed, reason: getaddrinfo ENOTFOUND ui.nordaun.com |
| `@nysgpt` | yes | unavailable | 0 | Error (FORBIDDEN): You are not authorized to access the item at https://gov.nysgpt.com/r/registry.json?limit=0. If this is a remote registry |
| `@openpolicy` | yes | unavailable | 0 | Error (NOT_FOUND): The item at https://www.openpolicy.sh/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@pacekit-gsap` | no | — | 28 | delisted from directory |
| `@phucbm` | yes | observing | 0 | Error (NOT_FOUND): The item at https://phucbm.com/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@pulkitxm` | yes | unavailable | 31 | Error (NOT_FOUND): The item at https://pulkit.page/components/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@pureui` | yes | unavailable | 0 | Error: Request to https://pure.kam-ui.com/r/registry.json?limit=0 failed, reason: Connect Timeout Error (attempted address: pure.kam-ui.com: |
| `@registrydirectory` | yes | degraded | 0 | mirror |
| `@sabraman` | yes | unavailable | 9 | Error: Request to https://sabraman.ru/r/registry.json?limit=0 failed, reason: getaddrinfo ENOTFOUND sabraman.ru |
| `@shark` | yes | unavailable | 96 | Error (NOT_FOUND): The item at https://shark.vini.one/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@shieldcn` | yes | unavailable | 3 | Error (NOT_FOUND): The item at https://shieldcn.dev/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@shoogle` | yes | healthy | 0 | Error (FETCH_ERROR): Failed to fetch from registry (400): https://shoogle.dev/r/registry.json?limit=0 |
| `@square-ui` | yes | unavailable | 0 | Error (NOT_FOUND): The item at https://square.lndev.me/registry/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@untld` | yes | unavailable | 2 | Error (NOT_FOUND): The item at https://ui.untldlabs.com/r/registry.json?limit=0 was not found. It may not exist at the registry. |
| `@w3-kit` | yes | unavailable | 0 | Error (FETCH_ERROR): Failed to fetch from registry (500): https://w3-kit.com/registry/registry.json?limit=0 |
| `@wandry-ui` | yes | unavailable | 0 | Error: Request to https://ui.wandry.com.ua/r/registry.json?limit=0 failed, reason: certificate has expired |
