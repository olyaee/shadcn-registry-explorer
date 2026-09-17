---
name: find-shadcn-components
description: >-
  Turn a UI/UX brief into a verified shortlist of shadcn/ui components drawn
  from this repo's local catalogue of 238 community registries (~37,837
  components in data/registries.enriched.json). Use when the user is building a
  UI feature and asks "what components could I use", "find shadcn components
  for X", "is there a registry component that does Y", wants to compare or
  combine registry components, or needs the exact install command / doc-page
  link for a community shadcn component. Not for authoring components or for
  the official shadcn/ui core primitives (those need no catalogue).
metadata:
  type: reference
---

# Find shadcn components from the local catalogue

This repo is a scraped index of the shadcn community registry directory. The
data is already on disk — never re-scrape or hit the network to search. Search
the local JSON, then verify links.

## Where the data lives

- `data/registries.enriched.json` — the search corpus. Shape:
  `{ registries: [ { handle, name, homepage, install, description, components } ] }`
  where `components` is `{ found, indexUrl, terminology, count, items: [...] }`
  and each item is `{ name, type, title, description }`.
  - `handle` is like `@corr`; the install id for an item is `@handle/name`
    (e.g. `npx shadcn add @corr/timeline`).
  - `type` is `registry:ui` | `registry:component` | `registry:block` |
    `registry:example` | `registry:lib` etc. Prefer `ui`/`component` for
    primitives; `block` for full sections/references.
  - ~11 registries have `components.found:false` (unresolved) — skip silently.
- `README.md` — human index of every registry with links to its browse pages.

## Procedure

1. **Decompose the brief into mechanics, not features.** "Overnight shift
   editor" → range-slider, draggable-timeline, time-picker, inline-rename,
   snap-to-step, segmented-control, spring-motion. Each mechanic becomes a
   keyword group.
2. **Score with the bundled script.** Edit the `GROUPS` dict in
   `scripts/search.py` to your mechanics and run it (see below). It scores every
   item by keyword hits across `name + title + description` and prints the top
   matches grouped by concept. Blocks-heavy dashboards score high on noise —
   read descriptions, don't trust rank alone.
3. **Shortlist per mechanic**, favouring `registry:ui`/`component` primitives
   over `block`s, and note when a `block` is only a *reference* to copy from.
4. **Verify the exact doc-page URL before sharing it.** The JSON stores only
   `homepage` and `indexUrl` — NOT per-component doc URLs, and each registry
   uses its own URL shape. Guessing 404s constantly. Open the site in the
   browser and read the real `href` (see Verification).
5. **Present** a per-mechanic table: component, exact doc link, install command.
   Offer a recommended *combination* when several compose into the feature.

## Running the search

```bash
python3 .claude/skills/find-shadcn-components/scripts/search.py
```

Edit the `GROUPS` dict at the top of the script first. Handle `None`
descriptions (`it.get('description') or ''`) — many items have null fields.

## Verification (the step that is always wrong if skipped)

Per-registry URL shapes vary wildly — examples confirmed by visiting:
`@corr` → `ui.corr.sh/components/<name>` · `@abui` → `abui.io/blocks/<name>` ·
`@scrollxui` → `scrollxui.dev/docs/components/<name>` · `@iconiq` →
`iconiqui.com/<category>/<name>` · `@beui` → `beui.dev/components/<group>/<name>`
· `@baselayer`/`@diceui` → `<site>/docs/components/<name>` · `@boldkit` →
`boldkit.dev/components/<name>` · `@aicanvas` → `aicanvas.me/components/<name>`
or `/design-systems/<ds>/<name>`.

Don't hardcode these — the reliable move is: open the registry's browse page in
the browser, extract anchors via JS, and read the true `href`:

```js
[...document.querySelectorAll('a')]
  .map(a => ({ t: a.textContent.trim(), h: a.getAttribute('href') }))
  .filter(x => x.h && /<your-keyword>/i.test(x.t + x.h))
```

## Traps this skill exists to remember

- **Platform mismatch.** Some catalogued registries are **React Native / Expo**
  (e.g. `@aniui`) — unusable in a shadcn *web* app. Check the site's framing
  before recommending.
- **JSON name ≠ site install id.** e.g. `@aicanvas` lists `glass-slider`, but the
  design-system variant installs as `@aicanvas/andromeda-slider`. Trust the
  install string printed on the actual component page.
- **SPA sites** are client-rendered; `WebFetch` often returns an empty shell or
  404s a guessed path. Use the browser tools, not WebFetch, to resolve links.
- **Blocks are sections, not primitives.** A `registry:block` is usually a whole
  page/section; recommend it as a copy-from reference, not a drop-in primitive.
