# shadcn component finder

~76k components from 394 shadcn community registries. Goal: for the feature the user is
building, a verified shortlist covering **every** UI piece. Run all commands via
`<repo>/find` (absolute path; self-installs on first run; `find --help`, `find graph --help`).

1. **Coverage map** — list every UI piece the feature needs, phrased as what it does or
   looks like ("grouped bar chart comparing a metric across groups", not "chart"). Walk:
   shell & nav · data display · inputs & filters · overlays · feedback & empty/loading/error
   states · flow & progress · motion · domain specifics. Done when a developer could build
   the feature from the map alone.
2. **Search** all pieces in one call:
   ```bash
   <repo>/find --brief - --kind component,block <<'JSON'
   {"piece": "what it does / looks like", "...": "..."}
   JSON
   ```
3. **Widen** strong hits: `find graph category "<label>"` (every library's version),
   `find graph similar @handle/name --other-registries`.
4. **Verify** finalists: description fits; link opens the item. Results carry ⚠ flags
   (and rank lower) for non-React libraries (`vue`, `svelte`, `react-native`…) and for
   whole registries that are `stale` (unreachable at last refresh) or `unavailable`.
5. **Deliver** per piece: 1–3 options with `npx shadcn add @handle/name`, doc link, why.
   End with a combination favouring one or two libraries.

**Done when** every piece has a recommendation or "no match → shadcn/ui core / build".

## Notes

- `no-page`/`companion` links mean no item page — use the registry homepage.
- Blocks are full sections: recommend as copy-from references.
- Confirm details on the doc page; its install string wins over `@handle/name`.
- Search folds icon variants (`fill/x`) and drops demos, so it reports fewer items than 76k.
- Queries are embedded via OpenAI (`OPENAI_API_KEY` in `<repo>/.env`); without a key,
  keyword-only ranking. `find update` refreshes data.
