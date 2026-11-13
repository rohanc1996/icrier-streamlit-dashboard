# AGENTS.md — ICRIER SIDE dashboard

Project instructions for OpenCode. Read this before changing anything.

## What this repo is

An interactive Streamlit companion to the **SIDE** digital-economy dataset
(71 countries, 60+ indicators, 2024–2027 editions). It reproduces and extends
the CHIPS composite index: CONNECT · HARNESS · INNOVATE · PROTECT ·
SUSTAINABILITY.

Pre-publication work: numbers may change, and nothing here should be quoted or
shared publicly without checking with the SIDE team.

## Commands

Run everything from the repository root.

```bash
# Environment (Python 3.10+; the venv already exists)
source .venv/bin/activate
# or call it directly:
./.venv/bin/python ...

# Dashboard
streamlit run SIDE_dashboard/dashboard.py

# CHIPS engine tests (no pytest needed)
cd SIDE_dashboard && ../.venv/bin/python -m tests.test_chips

# 2027 GDP-reference tests
./.venv/bin/python scripts/tests/test_gdp_reference.py

# Frozen-year regression check
./.venv/bin/python scripts/tests/frozen_years.py
```

Use the repo's `.venv`. Do not install packages globally; do not add a
dependency without asking first.

## Non-negotiable invariants

1. **Frozen years.** `data/SIDE 2024 - *.csv`, `2025`, and `2026` are the
   published record. Do not change them as a side effect of 2027 work. If a
   genuine correction is needed, say so explicitly and keep it in its own commit.
2. **2027 is additive.** New indicators live in `core/chips_hierarchy.py` under
   `_extend_2027` / the 2027 spec and apply only when 2027 data is loaded. They
   must not alter earlier editions' scores.
3. **Weights total 100% at every level.** The framework editor enforces this;
   any spec change must keep `validate_spec_totals` clean.
4. **Scaling is monotone per indicator, not across the composite.** For a single
   indicator, `full_minmax` and `z_score` are monotone transforms of the same
   column, so the country order never changes — no method may reorder countries
   on an indicator. The composite is different: it sums many differently-shaped
   transforms, and monotone transforms do not commute with sums, so the two
   methods **can and do** reorder countries overall (2026: 64 of 71 overall ranks
   differ, max 19 places; pillar ranks 312 of 355). This is intended and pinned
   by `core/rankings.py::composite_scaling_comparison` and the
   `chips_drank.max() > 0` check in `tests/test_chips.py`. Do not "fix" it, and
   do not claim in any document that overall ranks are method-independent.
5. **Rounding is part of the published method.** Indicator scores round to
   1 decimal on the 0–100 scale; aggregates carry full precision; the final
   CHIPS score rounds to 2 decimals (see `core/chips.py`). Don't "clean this up".
6. **Missing data is explicit, never silent.** Weight redistribution and group
   dropping follow the rules documented in `SIDE_dashboard/README.md` and the
   tests in `core/chips.py`. Read them before touching aggregation.

## Data layout

```
data/
├── SIDE <year> - Absolute.csv      # editions 2024–2027
├── SIDE <year> - Relative.csv      # 2026–2027
├── SIDE 2027 Connect Pillar.csv
├── 2027 individual indicators/     # raw source extracts (xlsx/csv) per indicator
├── 2027 pillar-wise/               # SIDE 2027 Absolute - <Pillar>.csv
├── reference/                      # GDP, schema, delta sheets
└── WIPO Global Innovation Index/   # GII provenance + panel extracts
```

CSV conventions:

- Read with `dtype=str, keep_default_na=False`, then `shrink_whitespace`,
  `normalize_column_name`, `_dedupe_columns`, `parse_numeric` from
  `core/loader.py`. Don't invent a second CSV reader.
- Country names are normalised through `SIDE_dashboard/components/country_names.py`
  and per-edition maps in `core/loader.py`.
- Trailing summary rows (`Coefficient of variation`) and `Unnamed: N` columns
  are not data.
- Preserve source precision. Round only where the published method says to.

## Code map

```
SIDE_dashboard/
├── dashboard.py          # entry point, page wiring, sidebar year selector
├── core/                 # logic: loader, scaling, chips, chips_hierarchy,
│                         # rankings, blend, correlations, columns
├── views/                # one module per page (chips_explorer, framework_editor,
│                         # country_explorer, scaling_comparator, ...)
├── components/           # ui.py, charts.py, country_names.py
├── assets/               # flags and static images
└── tests/test_chips.py   # CHIPS rule + integration tests
scripts/                  # dataset builders, reconciliation, per-source ingestion
  ├── data_sources/<source>/   # gdip, itu, oecd, undesa, world_bank, ...
  ├── analysis/             # ad-hoc analyses, one script per question
  └── tests/                # regression + reference tests
deliverables/               # blogs, CSVs and findings intended for humans
docs/decisions/             # short ADRs for methodology choices
```

`DEFAULT_YEAR = "2027"`; the sidebar only shows years whose files exist.

## Working style for this repo

- **Investigate before editing.** Print `shape`, `dtypes`, and a few rows before
  assuming a column name. Column drift between editions is the #1 source of bugs.
- **Prefer a saved script over a long inline heredoc.** Put exploratory analysis
  in `scripts/analysis/` and write its output to `deliverables/<task>/` or
  `data/derived/`. One script, one question, re-runnable.
- **Verify with numbers, not vibes.** When comparing dashboard output to a
  spreadsheet or published figure, show the country, indicator, both values and
  the delta.
- **Plan first for framework changes.** Anything touching `chips.py`,
  `chips_hierarchy.py`, `scaling.py`, or a published CSV should start in plan
  mode. Implement only after the approach is agreed.
- **Run the tests after any logic change** and say which ones you ran.
- **Keep `data/2027 pillar-wise/` and `SIDE 2027 - Absolute.csv` in sync.** A
  pillar CSV edit that isn't reflected in the combined file is a bug.
- **Never commit unless asked.** Keep the working tree clean enough to review.
- **Never launch Firefox.** It is the user's personal browser, so any invocation
  — including `--headless --screenshot` — attaches to their running instance,
  hijacks a tab and leaves a hung process behind. No Firefox, in any mode.
- **Browser verification is Safari**, via `safaridriver`. Two constraints worth
  knowing before you plan a check: Safari has **no headless mode**, so a driven
  session is a visible window that takes focus; and remote automation must be
  enabled once (`Develop → Allow Remote Automation`, or `sudo safaridriver
  --enable`, which needs the user's password — ask, never assume). Screenshots are
  viewport-only, so capture sections rather than whole pages.
- **If a check must not touch the screen**, use Playwright with its WebKit engine
  and say so in the report — WebKit is not Safari, and the difference matters when
  claiming browser compatibility. Never substitute Chrome or Edge unasked.

## OpenCode setup in this repo

Project agents (`.opencode/agents/`):

| Agent | Use for |
| --- | --- |
| `data` | dataset work, reconciliation, adding indicators, regression checks |
| `designer` | UI/UX, layout, charts, accessibility; may only edit `views/`, `components/`, `assets/`, `themes.py`, `dashboard.py` |
| `writing` | blogs, reports and emails; may only edit `deliverables/` |
| `research` | read-only web/source verification (subagent) |

Project commands (`.opencode/commands/`): `/indicator`, `/regress`,
`/audit-coverage`, `/blog`, `/ui-review`.

The `side-data` skill holds the CSV/country-normalisation conventions. Load it
before pandas work on `data/`.

## Writing conventions (deliverables and emails)

- Blog drafts: 800–900 words unless told otherwise, continuous essay (no section
  headers), concrete claims tied to the repo's own numbers.
- `deliverables/gii-eye-test/blog-draft.md` is **American** spelling;
  `blog-draft-british.md` is **British**. Don't convert one into the other
  unless asked.
- No "delve", no "in today's fast-paced world", no unsupported superlatives.
- Emails: direct, warm, short. Say what is attached and what is being asked.
