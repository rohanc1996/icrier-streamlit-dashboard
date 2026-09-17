# SIDE Dashboard

An interactive Streamlit companion to the SIDE digital-economy dataset
(71 countries, 60+ indicators). It mirrors and extends the analysis in the
companion notebook, wrapped in a point-and-click interface.

The sidebar year selector is edition-aware: the years 2025, 2026 and 2027 are
pre-registered in `core/loader.py`, and a year appears in the selector once at
least one of its `data/SIDE <year> - {Relative,Absolute}.csv` files is present.
The CHIPS hierarchy and its missing-data rules are shared across all years, and
column matching tolerates edition-specific header drift (shifting patent year
ranges, quarter ranges) via `core/columns.py`.

## Getting started

Requires **Python 3.10 or newer** (Streamlit 1.51 dropped Python 3.9).

```bash
# from the repository root
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r SIDE_dashboard/requirements.txt

streamlit run SIDE_dashboard/dashboard.py
```

Your browser opens at `http://localhost:8501`.

## Pages

| Page | What it does |
| --- | --- |
| 🏆 **CHIPS Index Explorer** | The CHIPS composite (CONNECT · HARNESS · INNOVATE · PROTECT · SUSTAINABILITY) with full missing-data transparency: leaderboard (scrollable race chart of thin coverage-coloured lines with country flags + sortable table), world map, per-country drill-down (treemap + what-if scenarios), a cross-country missing-data impact section, and the complete methodology. |
| 🎛️ **Create Your Own CHIPS Framework** | A thought-experiment editor: reweight or rebuild the CHIPS index (pillar / sub-pillar / indicator weights, indicator membership via per-row sub-pillar dropdowns, added dataset indicators), or override a country's individual indicator scores — then see how the whole leaderboard and each country's score and rank would change. Weights must total 100% at every level before results are shown; the published framework is never altered. |
| 🌍 **Country Explorer** | Three views: colour the world map by any indicator (click a country to open its rankings), inspect a single country's profile (headline metrics, full indicator ranking, strengths/weaknesses, score vs. the world median), or compare up to five countries on a spider chart. |
| ⚖️ **Scaling Comparator** | Compare the two scaling methods on any indicator and see which countries' scores swing most. |

## Concepts in the dashboard

- **Two scaling methods.** Raw values are mapped to 0–1 scores two ways so
  you can see how sensitive the rankings are to the choice. A sidebar selector
  sets the method used by the single-score pages (Country Explorer, CHIPS
  Explorer); the comparator page always shows both side by side:
  - *Full-range min-max* — simple, but a single extreme country can compress everyone else.
  - *Z-score (standardized)* (default) — each country's distance from the mean in standard
    deviations, mapped to 0–1 via the logistic curve. Ranks match plain
    z-scores, but the values stay on the same scale as the other method.
- **Pearson vs. Spearman.** Pearson measures linear correlation; Spearman ranks
  the data first, so it tolerates outliers. When the two disagree strongly, the
  link is driven by a few extreme countries.
- **Score = "goodness" (higher is better).** In comparison charts, each
  indicator is scaled with the selected method and inverted where a low raw
  value is better, so 1.0 always means "best on this indicator".

## The CHIPS composite index

The CHIPS Index Explorer aggregates **58 indicators** into **5 pillars**
(CONNECT · HARNESS · INNOVATE · PROTECT · SUSTAINABILITY). The three CHI pillars
(CONNECT, HARNESS, INNOVATE) each carry **25%** of the index and the two PS
pillars (PROTECT, SUSTAINABILITY) **12.5%** each; inside a pillar, sub-pillars
and indicators are weighted per the spec. The spec lives in
`core/chips_hierarchy.py`; the aggregation
engine (including the missing-data rules) in `core/chips.py`. Missing values
are handled explicitly rather than silently ignored:

- weights are equal inside a group unless the spec gives one;
- a missing component's weight is redistributed across its present siblings;
- more than half of a group missing drops the group, and the drop propagates up
  one level;
- a 2-component group with only 1 present is *kept* (survivor reweighted to
  100%) — an exception to the spec's 2-of-2 rule that matches the published
  spreadsheet, which scores each sub-pillar from whatever indicators are present;
- the INNOVATE → AI sub-pillar has two internal groups — the research pair
  (AI Innovation - Research + AI R&D score) and the remaining three AI
  indicators — aggregated with the same rules, except that a subgroup with even
  1 indicator present is kept and that member is weighed in full (the >50% drop
  rule does not apply inside these two AI subgroups);
- CHIPS itself requires at least 3 of the 5 pillars;
- indicator scores are rounded to 1 decimal place and the final CHIPS score to
  2 decimal places (0–100 scale) to match the published source.

Every decision is recorded per country, so the page can show *why* a score is
what it is — hover any treemap block or heatmap cell.

## Project layout

```
SIDE_dashboard/
├── dashboard.py              # entry point (streamlit run)
├── requirements.txt
├── core/                     # data + analysis logic (no UI)
│   ├── loader.py             # reads the CSV, friendly names, categories
│   ├── scaling.py            # the two 0–1 scaling methods
│   ├── rankings.py           # rank stability, profile ranks
│   ├── correlations.py       # pair preparation, leave-one-out, exclusions
│   ├── chips_hierarchy.py    # CHIPS spec: pillars, sub-pillars, weights, column map
│   ├── chips.py              # CHIPS aggregation engine + missing-data rules
│   └── themes.py             # the five notebook themes + highlight countries
├── components/
│   ├── charts.py             # every plotly figure builder (incl. the leaderboard race chart)
│   ├── country_names.py      # ISO3 <-> names, ISO2 -> emoji flags
│   └── ui.py                 # streamlit helpers (selectboxes, tables, config)
├── views/                    # one module per dashboard page
└── tests/
    └── test_chips.py         # CHIPS rule + integration tests (python -m tests.test_chips)
```