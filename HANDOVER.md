# HANDOVER — SIDE / CHIPS web prototype

Status: local, pre-publication prototype. Nothing here is signed off or citable.
Last updated: 20 November 2026.

This document covers the Astro site in `web/`. The Streamlit dashboard in
`SIDE_dashboard/` is a separate, internal tool and is not described here.

## Run it

```bash
# From the repository root
./.venv/bin/python pipeline/export_editions.py     # regenerate editions.json + CSVs
cd web
npm install
npm run dev        # http://localhost:4321
npm run build      # static output in web/dist
npm run verify     # headless WebKit checks + axe + screenshots
```

`predev` and `prebuild` run `scripts/sync-data.mjs`, which copies
`../data/derived/web` into `src/data/` and the downloads into `public/data/`.
Both are generated and gitignored.

The Streamlit CHIPS tests are unchanged and still run from the repo root:

```bash
cd SIDE_dashboard && ../.venv/bin/python -m tests.test_chips
```

## Where the numbers come from

Every score, rank and weight is produced by the engine in `SIDE_dashboard/core/`
through the canonical loader. The web layer never scores, re-weights or
re-ranks a country.

| Artefact | Producer | What it holds |
| --- | --- | --- |
| `data/derived/web/editions.json` | `pipeline/export_editions.py` | Every year × basis × method block, the multi-year tracker, group metadata and download links. |
| `data/derived/web/downloads/*.csv` | same | One CSV per year/basis, plus a combined file. |
| `data/derived/web/<year>/chips.json` | `pipeline/export_web_data.py` | The rankings page and country profiles (2026 Absolute, both methods). |
| `data/derived/web/series.json` | `pipeline/export_web_data.py` | The 2025→2026 comparison series. |

Source data: `data/SIDE <year> - Absolute.csv` and, for 2026 only,
`data/SIDE 2026 - Relative.csv`. GDP joins on ISO-3 from
`data/reference/GDP data for SIDE 2027.xlsx - side subset USD.csv`, column 2025.

## Editions and bases (the data limits)

- **2024**: Absolute only; 19 countries, 51 indicators.
- **2025**: Absolute only; 59 country names, **38 with a CHIPS score**.
- **2026**: Absolute, Relative and Combined (50–50); 71 countries, all scored.
- **2027 is deliberately not loaded.** Absolute values are missing sustainability;
  relative denominators are not final. Add it in `pipeline/export_editions.py`
  (`YEARS`) when the SIDE team signs it off.

Relative and combined are therefore disabled, with an inline reason, for 2024
and 2025. The bar shows the disabled option rather than hiding it.

## Pane inventory (7 panes)

| # | Pane | Reads | Notes |
| --- | --- | --- | --- |
| 1 | The field | `methods.*.field` | All scored countries, median, top-10 flags. Group selection mutes non-members; it never removes them. |
| 2 | Every score, ranked | `methods.*.field` | All countries by default; an explicit “show” control can cut to 25 or 10. |
| 3 | Anatomy of a score | `methods.*.composition` | Weighted pillar contributions, all countries by default, explicit “show” control. |
| 4 | Five verdicts | `methods.*.verdicts` | Follows the first comparison country (India if unset). Pillar ranks only. |
| 5 | Rank tracker | `tracker[method][window]` | Ranks only. Countries scored in every selected year, re-ranked within that subset. |
| 6 | Two scales, one index | `robustness` | Sortable table; default order is smallest absolute rank difference. |
| 7 | Scale and score | `methods.*.sizeVsScore` | GDP 2025 on a log axis. Does not follow the year selector. |

Removed: the old coverage pane (pane 8) and the cross-edition score dumbbells.
The old normalization bar chart became pane 6's table.

## Controls and state

The filter bar is `web/src/components/FilterBar.tsx`; state lives in the URL and
is read/written by `web/src/lib/site.ts`.

| Control | URL | Default |
| --- | --- | --- |
| Score basis | `basis=absolute\|relative\|combined` | `combined` (2026) |
| Years | `year=2025,2026` | `2026` |
| Country grouping | `group=all\|g20\|g20em\|custom` | `all` |
| Custom group | `countries=IND,USA,…` | empty |
| Two-country comparison | `compare=IND,USA` | empty |
| Normalization | `scale=minmax\|z` | `minmax` |
| Pane | `pane=1…7` | `1` |

Defaults are omitted from the URL, so pasting a link restores exactly the
non-default parts. “Reset view” clears the query string.

The normalization control sits inside “Advanced / methodology”. Whether public
readers should see it is an open question; the single switch is
`SHOW_NORMALIZATION_CONTROL` in `web/src/lib/site.ts`. Setting it to `true`
renders the control inline instead.

Country groups are defined once, in `pipeline/export_editions.py` (`G20`,
`G20_EMERGING`), and travel to the site in `meta.groups`. The `BLOC` column in
the Relative CSVs is **not** usable (17 rows, wrong membership).

## What is deliberately not built

- **2027**: not loaded.
- **CHIPS with / without AI**: the filter state is general enough to hold a
  second index, but no such view exists.
- **Score comparison across years**: never shown. The tracker is ranks only.
- **Population / per-capita GDP**: no population series in the repo.
- **Networks or inline explanation of the normalization maths**: the
  methodology page carries the method.
- **Automatic flag fetching**: flags are vendored. A top-10 country without a
  vendored SVG renders as a dot. Add the SVG under `web/src/assets/flags/` and
  its ISO-2 to `VENDORED_FLAGS` in `site.ts` when the flagged set changes.

## Known data issues to raise with the SIDE team

1. The brief's “38 countries continuous 2025–2027” is really “38 countries with
   a score in 2025”; 57 country names appear in all three files, and 2026
   scores 71. The tracker's subset is therefore 38 for 2025→2026 and 19 once
   2024 is selected.
2. There is no 2022 or 2023 data in the repository, so the promised 2023 hook
   is a configuration placeholder, not a data gap that can be filled here.
3. `BLOC` in the Relative files is incomplete and inconsistent with G20
   membership; group membership is metadata in the export.
4. GDP is a single 2025 vintage; pane 7 cannot follow the year selector.
5. 2024 and 2025 have no Relative file, so the basis selector is year-gated.
6. Some unpublished indicators sit outside the framework; they are listed on
   the methodology page and carry no index weight.

## Design tokens

Palette, type, spacing and radii are in `web/src/styles/tokens.css`. The only
other place a colour is defined is a handful of component-local tints in
`web/src/styles/global.css` (muted marks, delta pills). A designer can change
the palette in `tokens.css` without touching the data layer.

## Tests

`npm run verify` drives Playwright WebKit (not Safari, not Firefox, not
Chrome) headless at 1400×1000, 1366×768, 390×844 and 320×800. It checks:

- seven panes, pane navigation, keyboard, deep links and reset;
- the filter bar's controls, disabled basis options, and the active-view line;
- all-country defaults and explicit top-N controls;
- the tracker is ranks-only and uses the 38-country subset;
- the robustness table's default order and header sorting;
- downloads resolve to non-empty CSVs;
- axe-core on 18 page states;
- no horizontal overflow on mobile or at 1366×768.

Screenshots and `report.json` land in `web/.verify/` (gitignored).

## Open questions

1. Should public readers see the normalization selector at all? (Currently
   behind “Advanced / methodology”; flip `SHOW_NORMALIZATION_CONTROL`.)
2. Should there be a “CHIPS with / without AI” view? The bar can carry it; the
   view is not built.
3. Final branding and typography — a designer decides; tokens are extractable.
