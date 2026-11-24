# SIDE Report web prototype

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

`overview.json` is copied alongside it and feeds the `/` carousel. If it is
missing, the build still runs and the two built panes are derived from
`chips.json`; the build log says which source was used.

## Routes

| Route | Page |
| --- | --- |
| `/` | **Overview** — the six-pane carousel and the global filter bar |
| `/rankings` | Rankings table, filter, sort, pillar columns, scale switch |
| `/country/[iso3]` | Country profile with the L1–L3 pillar → sub-pillar → indicator drilldown |
| `/methodology` | The seven spec sections, live counts and both scaling methods |
| `/about` | Status, scope and credits |

Nav is Overview · Rankings · How the index works · About. Country profiles keep
the Rankings tab current.

## The overview carousel

`/` is one pane at a time — not a scroll-snap strip. `src/components/
OverviewExplorer.tsx` is the stateful part; it renders `FilterBar` and the seven
panes from `src/lib/site.ts`, from `data/derived/web/editions.json`.

- Prev/next chevrons, a `3 / 7` counter and a dot stepper; Home/End and ←/→
  also move. Focus is never moved for you.
- **The filter bar drives every pane.** Score basis, one or more years, country
grouping, a two-country comparison and normalization are read from the URL by
`src/lib/site.ts`. `?pane=3&year=2025,2026&basis=absolute&group=g20` is a
shareable view.
- **Pane 6 is exempt from the method toggle** because it compares the two
  methods, and its caption says so.
- `role="group"`, `aria-roledescription="carousel"`, an `aria-label`, and a
  polite live region that announces "Pane 3 of 8: Anatomy of a score".
- No autoplay. `prefers-reduced-motion: reduce` removes the pane transition.
- Every pane carries its section number and title, a one-line "what this
  shows", the chart, a **View as table** disclosure and a method-note line
  (edition · method · N).

The six panes, in order: The field; Every score, ranked and explained; Five
verdicts; Rank tracker; Two scales, one index; Scale and score.

**Built now (all six panes):** the field, every score ranked and split into its
weighted composition with an explicit top-N control (all by default),
the selected country's five pillar verdicts, the multi-year rank tracker, the
sortable robustness table that replaces the diverging bars, and the GDP scatter
on a log axis. Every table fallback carries the same numbers as its chart.
Every chart is produced at build time: geometry comes from `d3` scale maths and
`src/lib/site.ts`, and Astro prerenders the SVG into the HTML.

- **Pane 5 is ranks only.** It covers the countries scored in every selected
  edition, re-ranked within that subset, and says that the methodology,
  indicators and weights changed between editions.
- **Pane 6 is a table, not a bar chart.** It sorts by the smallest absolute
  rank difference by default and states that individual indicator ranks cannot
  move (z-score is monotone with min–max); only the composite can.
- **Pane 7 uses a log GDP axis** with magnitude ticks ($50bn … $30tn). The
  Absolute edition scores volumes, so the relationship is partly
  definitional; the caption says so, and GDP does not follow the year control.
- **The old coverage pane is removed.** Coverage survives as a download column
  and a caveat on the rankings page.

`d3` is pinned to **7.9.2** and used at build time only — no chart runtime
library ships to the browser. Pane 5 reads `movement.years` from the data, so a
2027 edition extends the panel without a rewrite.

### Flags in panes 1, 2, 7 and 8

With no grouping chosen, the ten best scores are drawn as round country flags
instead of dots, in the beeswarm (pane 1) and the scatter (pane 7). Selecting a
grouping (G20, the European Union, ASEAN, SAARC, the African Union, the Arab
League, Mercosur or a custom set) flags **every member of that grouping** and
demotes every other country — including the global top ten outside the group —
to a dot. Each flag is centred on the exact data position and allowed to
overlap. Paint order is rank order — lowest flag rank first, rank 1 last — so
the best score is on top. Every flag is focusable and reveals a 22px flag plus
a "country, score" label when hovered or focused; the reveal is CSS-only (a
general sibling combinator from `.flag-mark--us` to the overlay layer that
closes the SVG), so a buried mark stays reachable by keyboard and by tap.

Everything outside the flagged set is a dot, and every dot is interactive too:
a transparent hit circle expands the small mark, the group is focusable, and
the same CSS pattern (`.chart-point--aus` → `.point-overlay--aus`) reveals a
ring and the same "country, score" chip. The rule is generated for every point
in `FlagSprite.astro` from `overviewPointIso3s()`; no per-point markup or
sprite file is needed, because the overlay shows the label without a flag
image. Dots come before flags in document order, so flags still paint on top.

Pane 2 draws a flag at every stem tip — all 15 rows — at 15px (13px at
≤640px). Those flags are decorative: the row already prints the country name
and score as text, so the mark is `aria-hidden` and takes no tab stop, and
there is no overlay to reveal.

- The flagged set is **derived** from the active method's `field.values` and
  the selected grouping, not hard-coded. It genuinely differs by method and by
  group, so the page's sprite carries every scored country. The shared rule
  lives in `src/lib/flags.mjs` and is used by the build, the fetch script and
  `scripts/verify.mjs`, so the three cannot drift.
- The symbols live in `web/src/assets/flags/<iso2>.svg`, vendored by
  `node scripts/fetch-flags.mjs` (dev-time only; run it when the flagged set
  changes). The command reads `data/derived/web/editions.json` and downloads
  only the missing files from HatScripts/circle-flags (MIT). The SVGs are
  committed, so builds are offline. An unmapped alpha-3 fails the run loudly.
  Because a custom grouping can name any country, all 71 are vendored.
- `src/components/FlagSprite.astro` inlines each file **once** as a `<symbol>`
  and rewrites its internal ids (`mask id="a"` → `ca-a`) so many flags can
  share one document. Marks reference it with `<use href="#flag-us">`; there is
  one sprite per page, outside the carousel island, so the method toggle never
  duplicates it.
- The marks themselves are one component (`FlagMark`, with `FlagOverlay` for
  the label layer), shared by all four panes.
- Size is 18px on desktop and 14px at ≤640px (a centre-anchored scale, so the
  data position does not move); the 1.5px `--surface` ring keeps overlapping
  flags legible as chips.

## Data contract for `/`

`data/derived/web/editions.json` (produced by `pipeline/export_editions.py`):

```
meta      { years, methods, defaultMethod, defaults, basisAvailability,
            groups, groupLabels, editionCountryCount, gdpYear, leaves, edition }
editions  { "<year>": { "<basis>": {
              methods: { full_minmax: PaneData, z: PaneData },
              robustness: [{ iso3, country, rankFull, rankZ, delta }],
              countryCount, scoredCount } } }
tracker   { "<method>": { "2025,2026": { years, countries[{ iso3, ranks }], count } } }
downloads [{ label, href, note }]
```

`PaneData` carries `field { values, median, min, max }`, `composition[]`
(all countries, each pillar with `contribution`), `verdicts { pillars, countries }`
and `sizeVsScore[]`. Ranks are exported by the engine; the site never derives
one. `tracker` carries **ranks only** — no score appears in it, by construction.

Scores are 0–1. `src/lib/format.ts` is the one place that multiplies by 100:
2 dp for composites, 1 dp for indicator and pillar scores.

## Verify (headless WebKit)

```bash
npm run build
npm run verify     # node scripts/verify.mjs
```

`scripts/verify.mjs` serves `dist/` itself on a free port, drives Playwright's
WebKit engine headless at 1400×1000, 1366×768, 390×844 and 320×800, and asserts:

- `/` renders exactly 6 panes with one visible; next/prev, ←/→, Home/End and
  `?pane=` change it; the live region and counter follow.
- The filter bar is one compact row and scrolls with the page; it opens its
  controls as a collapsible panel that pushes the panes down and Escape closes.
- The filter bar reports the active view in text, a deep link restores basis,
  years, group, comparison and pane, and “Reset view” clears the query string.
- A basis with no file for the selected year is disabled with a reason.
- Pane 2 defaults to all countries and only cuts on an explicit top-N choice.
- Pane 5 is ranks only and uses the 38-country 2025→2026 intersection; its
  rank ladder labels every selected year and the table carries each year's rank
  and the year-on-year move.
- Pane 6 sorts by the smallest absolute difference by default and each header
  sorts.
- Downloads resolve to non-empty CSVs.
- `/rankings` defaults to z-score; the movement column is labelled against the
  other method.
- axe-core on eighteen page states; no horizontal overflow at 390px or at
  1366×768.

Screenshots and `report.json` land in `.verify/` (gitignored). Violations are
printed for triage and do not fail the run; behaviour checks do.

Playwright is pinned to **1.61.1**: on macOS 14, 1.65.x installs WebKit build
2251 but sends `Page.overrideSetting: PushAPIEnabled`, which that build rejects,
so every page fails to open. Never point this at Firefox, Chrome or a headed
browser.

Design tokens and the type scale are in `src/styles/tokens.css` and
`src/styles/global.css`. The structure follows `docs/ai-index-ia.md` §6; the
palette is ICRIER's, with orange reserved for fills, rules and marks — never
text (`--accent-ink` is the only orange text token, and only where sanctioned).

Cream is the page ground, not the only surface. `--wash-warm` (warm sand) sits
on the page head, the carousel control bar and the country masthead, with the
orange rules doing the punctuation. `--wash-accent` (pale orange) sits behind
the active nav item. The footer is the one dark surface, `--brand` navy with
`--footer-fg` / `--footer-fg-muted` text. A 4px five-pillar strip closes the
header; its hard stops are built from each pillar's published weight, not five
equal slices. Colour that means "pillar" stays in the five pillar tokens: the
country page cards take their pillar's tint, and methodology rows take a tinted
gradient plus a pillar-colour left edge. Data marks themselves stay neutral.

The ICRIER mark in the header lockup is vendored to
`web/public/brand/icrier-logo.png` by `node scripts/fetch-brand.mjs`, with the
same dev-time-only rule as the flags: the PNG is committed, so builds stay
offline, and the script pins the source's 180×97 dimensions because the header
reserves layout space from them. It is ICRIER's trademark, not an open-licence
asset — fine on this local prototype, and not to be redeployed publicly or
redistributed separately without sign-off.

No deploy config, CI, analytics or CMS. Not for citation: the data is
pre-publication.
