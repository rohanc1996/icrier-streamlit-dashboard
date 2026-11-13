# SIDE · CHIPS web prototype

Local Astro prototype for the SIDE 2026 CHIPS index. Part of the repo's
`web/` tree; it does not touch the Streamlit dashboard or the data files.

## Run

```bash
cd web
npm install
npm run dev      # http://localhost:4321
npm run build    # static output in web/dist
```

`predev` and `prebuild` run `scripts/sync-data.mjs`, which copies
`../data/derived/web` into `src/data/` (gitignored). The script fails loudly
unless `chips.json` is contract v2:

```
meta      { edition, methods: ["full_minmax","z"], defaultMethod, countries, leaves, ... }
framework { pillars[] }
methods   { full_minmax: { scores[], indicators[] }, z: { ... } }
```

## What is here (Wave 2b)

- `/` — rankings table, filter, sort, rank/score emphasis, pillar columns,
  and the min–max / z-score scale switch. The scale lives in the URL
  (`?scale=z`); min–max is the default. When z-score is active the table adds
  a **Rank vs min–max** column. The CHIPS composite is shown to 2 decimals;
  indicator and pillar scores to 1.
- `/country/[iso3]` — profile with the L1–L3 drilldown: pillar cards →
  sub-pillars → indicators. One pillar is open at a time; SUSTAINABILITY opens
  straight onto its six indicators. The open panel lives in the URL
  (`?open=harness` / `?open=harness.ai`) alongside `?scale=`.
- `/methodology` — the seven spec sections, live counts and both scaling
  methods.
- `/about` — status, scope and credits.

`Change vs 2025` is deliberately disabled: the comparison series and its
eligible-country rule are not wired in this wave.

## Verify (headless WebKit)

```bash
npm run build
npm run verify     # node scripts/verify.mjs
```

`scripts/verify.mjs` serves `dist/` itself on a free port, drives Playwright's
WebKit engine headless at 1400×1000, 390×844 and 320×800, asserts the rankings/
profile/drilldown/methodology behaviour, runs axe-core on six page states, and
writes screenshots plus `report.json` to `.verify/` (gitignored). Violations are
printed for triage and do not fail the run; behaviour checks do.

Playwright is pinned to **1.61.1**: on macOS 14, 1.65.x installs WebKit build
2251 but sends `Page.overrideSetting: PushAPIEnabled`, which that build rejects,
so every page fails to open. Never point this at Firefox, Chrome or a headed
browser.

Design tokens and the type scale are in `src/styles/tokens.css` and
`src/styles/global.css`; they follow `docs/ai-index-ia.md` §6.

No deploy config, CI, analytics or CMS. Not for citation: the data is
pre-publication.
