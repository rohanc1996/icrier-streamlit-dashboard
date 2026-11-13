# AI index website — prototype plan (2026 edition)

- **Status:** building. Prototype scope locked 2026-11-13.
- **Origin:** recovered from OpenCode session `ses_e2c766768ffe18biEgXzPgRQNM`
  ("Building AI index dashboard website"), which reverse-engineered
  `observer.co.uk/data/global-ai` as a reference.
- **Supersedes:** the earlier version of this file, which specified the 2027
  edition, 62 indicators and an Absolute/Relative toggle. All three were wrong.

## What changed from the original plan, and why

| Original | Now | Why |
|---|---|---|
| 2027 edition | **2026** | 2027 Absolute is 44% empty (2583/5893 cells); 2026 is 6% empty |
| Absolute **and** Relative | **Absolute only** | `SIDE 2026 - Relative.csv` has **17 of 71** countries; 2027 Relative has 0 |
| 62 indicators | **58 CHIPS leaves** | 2026 CSV → 71 loadable indicators → 58 in the framework, 13 outside it |
| Absolute/Relative bubble chart | dropped | No Relative data to compare |
| Scrollytelling, bump chart, radar | deferred | Cost sits in transitions, not charts; not needed to prove the prototype |
| Cloudflare/Vercel + CI | **local only** | Prototype runs on a laptop; hosting decided later |
| ISO3 mapping "to be built" | **already exists** | `COUNTRY_TO_ISO3` in `components/country_names.py`, 73 entries, 71/71 coverage for 2026 |

Recovered plan, for reference: reuse `SIDE_dashboard/core/` for index logic, rebuild
presentation in Astro/D3, export a JSON contract, keep Streamlit as the internal
analyst tool.

## Scope

**In:** rankings table (71 countries, sortable, rank/score toggle); all 71 country
profiles; drilldown through 5 pillars → 16 sub-pillars → 58 indicators; rank change
2025→2026 for the 52-country intersection; methodology + caveats page.

**Out:** Relative dataset, blend, Absolute/Relative toggle, bubble chart,
scrollytelling, animated bump chart, radar charts, hero animation, CMS, analytics,
hosting, CI, non-English.

Frozen editions are read-only inputs. Nothing under `data/SIDE <year> - *.csv`
changes; the exporter writes only to `data/derived/web/`.

## Data facts (verified 2026-11-13)

| Edition | Countries | Columns | Empty cells | Verdict |
|---|---|---|---|---|
| 2024 Absolute | 19 | 52 | — | too small for a time series |
| 2025 Absolute | 59 | 49 | — | usable as a comparison point |
| 2026 Absolute | **71** | 78 | **6%** | **the edition we publish** |
| 2027 Absolute | 71 | 84 | 44% | not ready |
| 2026 Relative | 17 | 78 | 16% | out of scope |
| 2027 Relative | 0 | 80 | — | empty stub |

Country intersections: 2026∩2027 = 71, 2025∩2026∩2027 = 52, 2024∩2025∩2026 = 15.
Time series is restricted to **2025∩2026 = 52** countries, per the rule that only
countries common across the included years may be compared.

2026 composition: 78 raw columns → 71 loadable indicators → **58 CHIPS leaves** +
13 columns outside the framework (including a junk `Count` column and a corrupted
`gap - ... neeGenderd ...` header). The 13 are excluded from the index but must be
listed in `meta.excludedFromIndex` — missing data is never silent.

## Scoring rules the exporter must not reinvent

- Scores are **0–1** end to end. Never emit 0–100.
- Leaf scores: rounded to 1 decimal on the 0–100 scale (`chips.py:171`).
- Aggregates consume the **rounded** leaf scores, so aggregates must come from
  `aggregate_country`/`tree_to_frame` — never recomputed from `score_matrix`.
- Final CHIPS: rounded to 2 decimals on the 0–100 scale (`chips.py:352`).
- Method: **both** are exported — `full_minmax` and `z` — and the prototype toggles
  between them. `meta.defaultMethod` is `full_minmax`. Note the Streamlit dashboard
  still defaults to `METHOD_Z`; the two defaults deliberately differ for now.
- Scaling uses all 71 countries; filtering before scoring changes every number.

## Contract

```
meta        edition, generated, method, countries, leaves, excludedFromIndex[]
framework   pillars[] -> subPillars[] -> leaves[]
scores      one row per country: overall, rank, coverage, pillars{}, subPillars{}
indicators  one row per country×leaf: raw, score, status, reason, rank, of, effectiveWeight
series      2025∩2026 only: {iso3, year, overall, rank}
```

`scores.json` + `indicators.json` under `data/derived/web/2026/`, `series.json` at
`data/derived/web/`. Validated by `pipeline/validate_web_data.py` against a
checked-in JSON Schema.

## Layout

```
pipeline/            Python exporter + schema + validator   (data agent)
data/derived/web/    generated JSON, never hand-edited      (generated)
web/                 Astro site, local only                 (designer agent)
docs/ai-index-ia.md  IA and drilldown design spec           (designer)
```

`web/` is deliberately separate from `SIDE_dashboard/`: the Streamlit app stays the
internal analyst tool, the site is the public artefact.

## Stack (licences verified 2026-11-13)

| Item | Choice | Licence |
|---|---|---|
| Framework | Astro 7.4.11 (needs Node ≥ 22.23.4; local Node is 26) | MIT |
| Charts | D3 7.9.2 | ISC |
| Schema validation | ajv 8.20.0 | MIT |
| QA | Playwright 1.65 + axe-core 4.14 | Apache-2.0 / MPL-2.0 |
| Display type | Newsreader | OFL, no reserved name |
| UI type | Inter | OFL, no reserved name |
| Flags | `lipis/flag-icons` (MIT); emoji is the interim fallback | MIT |

IBM Plex Sans is **not** used despite the original plan naming it: it carries a
reserved font name ("Plex"), which complicates subsetting. Observable Plot is
allowed for quick marks but the signature charts are D3 — Plot is still pre-1.0.

A `/credits` page must list the OFL fonts, ISC/MIT libraries and flag set.

## Gates

**G1 — numeric reconciliation (blocks everything).** For India, Brazil and Costa
Rica: overall, all 5 pillars, rank and 3 sample indicators must match the engine
at **exactly zero delta**. 71 countries. `git status data/` clean.

**G2 — design review.** IA spec approved before any component is built.

**G3 — local QA.** Keyboard path through the rankings table, contrast checked,
table equivalent for every chart, `prefers-reduced-motion` respected, Lighthouse
run locally.

## Open items

1. **Resolved:** both methods are exported and the prototype toggles between them.
   Ranks are *not* method-independent — see invariant 4 in `AGENTS.md` and
   `deliverables/website-prototype/method-comparison.md`. Before any public launch,
   one method must be named official; two league tables is a prototype affordance,
   not a publishing policy.
2. Pillar ranks follow `rankings.py:172-180` (round to 2dp on 0–100, then min-rank).
   The dashboard does this outside `chips_table`; confirm nothing else overrides it.
3. 2025→2026 rank change mixes two editions with different indicator sets and
   hierarchies. It ships with a visible caveat or not at all.
4. Emoji flags degrade to two letters on Windows Chrome; swap to `lipis/flag-icons`
   before any public launch.
