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

`overview.json` is copied alongside it and feeds the `/` carousel. If it is
missing, the build still runs and the two built panes are derived from
`chips.json`; the build log says which source was used.

## Routes

| Route | Page |
| --- | --- |
| `/` | **Overview** — the eight-pane carousel |
| `/rankings` | Rankings table, filter, sort, pillar columns, scale switch |
| `/country/[iso3]` | Country profile with the L1–L3 pillar → sub-pillar → indicator drilldown |
| `/methodology` | The seven spec sections, live counts and both scaling methods |
| `/about` | Status, scope and credits |

Nav is Overview · Rankings · How the index works · About. Country profiles keep
the Rankings tab current.

## The overview carousel

`/` is one pane at a time — not a scroll-snap strip. `src/components/
OverviewCarousel.tsx` is the only stateful part; the eight panes live in
`src/lib/overview.ts` and are rendered by Astro at build time, then hydrated.

- Prev/next chevrons, a `3 / 8` counter and a dot stepper; Home/End and ←/→
  also move. Focus is never moved for you.
- **The scale toggle re-scores the whole carousel.** Both methods are built at
  build time; the island only chooses a block. The default is the payload's
  `meta.defaultMethod` (z-score), so `?scale` is absent by default and
  `?scale=minmax` selects the alternative. The URL is the source of truth and
  changes use `replaceState`; `?scale=z` normalises to absent.
- **Pane 6 is exempt** because it compares the two methods, and its caption
  says so.
- `?pane=3` and `?scale=minmax` are shareable and survive a reload, together.
  The default pane is never written to the URL, the same convention as
  `?scale=` on `/rankings`.
- `role="group"`, `aria-roledescription="carousel"`, an `aria-label`, and a
  polite live region that announces "Pane 3 of 8: Anatomy of a score".
- No autoplay. `prefers-reduced-motion: reduce` removes the pane transition.
- Every pane carries its section number and title, a one-line "what this
  shows", the chart, a **View as table** disclosure and a method-note line
  (edition · method · N).

The eight panes, in order: The field; The podium and the pack; Anatomy of a
score; India's five verdicts; Movement; The same index, two scales; Scale and
score; How much stands behind a score.

**Built now (all eight panes):** the field (71 dots, median tick, India
marked), the top-15 lollipop, the weighted composition of the top 10, India's
five pillar verdicts against all 71 ranks, the score dumbbell across editions,
the diverging bars between the two scaling methods, the GDP scatter on a log
axis, and the coverage scatter. Every table fallback carries the same numbers
as its chart. Every chart is produced at build time: geometry comes from `d3`
scale maths and `src/lib/overview.ts`, and Astro prerenders the SVG into the
HTML.

- **Pane 5 encodes score, not rank.** Ranks are positions in a country pool
  that changed composition between editions (59 → 71 countries, and 2025 used
  a smaller indicator set), so a rank slope reads as performance when it is
  mostly composition. The rank columns stay in the table.
- **Pane 6 states its headline in the pane** — how many of the 71 change rank
  between min–max and z-score — and the bars run from a zero line.
- **Pane 7 uses a log GDP axis** with magnitude ticks ($50bn … $30tn). The
  Absolute edition scores absolute volumes, so the relationship is partly
  definitional; the caption says so.
- **Pane 8 marks the countries below 80% coverage** and states the unscored
  sub-pillar cell count. Coverage is a caveat on a rank, not a penalty.

`d3` is pinned to **7.9.2** and used at build time only — no chart runtime
library ships to the browser. Pane 5 reads `movement.years` from the data, so a
2027 edition extends the panel without a rewrite.

### Flags in panes 1, 2, 7 and 8

The ten best scores are drawn as round country flags instead of dots, in the
beeswarm (pane 1) and both scatters (panes 7–8). Each is centred on the exact
data position and allowed to overlap. Paint order is rank order — rank 10
first, rank 1 last — so the best score is on top. Every flag is focusable and
reveals a 22px flag plus a "country, score" label when hovered or focused; the
reveal is CSS-only (a general sibling combinator from `.flag-mark--us` to the
overlay layer that closes the SVG), so a buried mark stays reachable by
keyboard and by tap. Everything below the top 10 stays a plain dot.

Pane 2 draws a flag at every stem tip — all 15 rows — at 15px (13px at
≤640px). Those flags are decorative: the row already prints the country name
and score as text, so the mark is `aria-hidden` and takes no tab stop, and
there is no overlay to reveal.

- The flagged set is **derived** from the active method's `field.values`, not
  hard-coded. It genuinely differs by method — min–max flags ARE, z-score flags
  CAN — so the page's sprite carries the union. The shared rule lives in
  `src/lib/flags.mjs` and is used by the build, the fetch script and
  `scripts/verify.mjs`, so the three cannot drift.
- The symbols live in `web/src/assets/flags/<iso2>.svg`, vendored by
  `node scripts/fetch-flags.mjs` (dev-time only; run it when the flagged set
  changes). The command reads `data/derived/web/overview.json` and downloads
  only the needed files from HatScripts/circle-flags (MIT). The SVGs are
  committed, so builds are offline. An unmapped alpha-3 fails the run loudly.
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

`data/derived/web/overview.json` (produced by the data agent):

```
meta          { edition, generated, methods, defaultMethod, countries, gdpYear, gdpSource }
methods       {
  full_minmax: { field, top15, composition, india, movement, sizeVsScore, coverage, correlation },
  z:           { ... same structure ... }
}
scaleMovement { pairs, movers: [{ iso3, country, rankFull, rankZ, delta }] }
```

Per method: `field { median, min, max, values[] }`, `top15[]`,
`composition[]` (pillars with `contribution`), `india { pillars[], best, worst }`,
`movement { years, countries: [{ iso3, country, ranks, scores }] }`,
`sizeVsScore[]`, `coverage[]`, and `correlation { pearson, spearman,
pearsonExTop2, spearmanExTop2, n }`. `scaleMovement` sits outside `methods{}`
because it compares them.

Scores are 0–1. `src/lib/format.ts` is the one place that multiplies by 100:
2 dp for composites, 1 dp for indicator and pillar scores. `india.best` and
`india.worst` are objects (`{ id, rank }`), and `composition[].contribution`
is used as exported — never recomputed.

Pane 5 needs a score per edition; the method block carries
`movement.countries[].scores`, with `src/data/series.json` as the fallback and
the ranks in the two files compared at build time so the dumbbells and the
table cannot drift apart.

## Verify (headless WebKit)

```bash
npm run build
npm run verify     # node scripts/verify.mjs
```

`scripts/verify.mjs` serves `dist/` itself on a free port, drives Playwright's
WebKit engine headless at 1400×1000, 390×844 and 320×800, and asserts:

- `/` renders exactly 8 carousel panes with one visible; next/prev, ←/→,
  Home/End and `?pane=` change it; the live region and counter follow.
- Every pane draws a real chart and a real table; no placeholder is left.
- Pane 1 draws 71 dots plus a median tick and an India mark; pane 2 draws 15
  lollipop rows; pane 5 draws one dumbbell per movement country with the five
  largest score changes marked and the live caveat count; pane 6 draws 10
  diverging rows and states its 64-of-71 headline; pane 7 draws 71 points on a
  log axis with magnitude ticks and India labelled; pane 8 draws 71 points and
  marks the 9 below 80% coverage. Every table matches its chart.
- `/rankings` defaults to z-score; the movement column compares against the
  other method and is labelled accordingly ("Rank vs min–max" / "Rank vs z").
- The scale toggle drives every overview pane (pane 6 excepted), and
  `?pane=4&scale=minmax` restores both the pane and the method.
- The profile drilldown, `?open=`, the methodology page and 320px layout.
- axe-core on eighteen page states (both methods), the orange-never-text guard
  on `/`, both scales, panes 4–8, `/rankings` and `/country/IND`, and no
  horizontal scroll at 390px for both overview scales and panes 3–8.

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

No deploy config, CI, analytics or CMS. Not for citation: the data is
pre-publication.
