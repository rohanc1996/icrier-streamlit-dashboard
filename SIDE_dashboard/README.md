# SIDE Digital Economy Dashboard

An interactive Streamlit companion to the SIDE 2026 digital economy dataset
(71 countries, 60+ indicators). It mirrors and extends the analysis in the
companion notebook, wrapped in a point-and-click interface.

## Getting started

```bash
# from the repository root
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r SIDE_dashboard/requirements.txt

streamlit run SIDE_dashboard/dashboard.py
```

Your browser opens at `http://localhost:8501`.

## Pages

| Page | What it does |
| --- | --- |
| 🌍 **Country Explorer** | Three views: colour the world map by any indicator (click a country to open its rankings), inspect a single country's profile (headline metrics, full indicator ranking, strengths/weaknesses, score vs. the world median), or compare up to five countries on a spider chart. |
| 🏆 **CHIPS Index Explorer** | The CHIPS composite (CONNECT · HARNESS · INNOVATE · PROTECT · SUSTAINABILITY) with full missing-data transparency: leaderboard, world map, per-country drill-down (treemap + what-if scenarios), a cross-country missing-data impact section, and the complete methodology. |
| ⚖️ **Scaling Comparator** | Compare the four scaling methods on any indicator. Adjust the cap window with sliders and see which countries' ranks swing most. |
| 🔬 **Correlation Explorer** | Pick any two indicators. Get four-panel scatter plots (full / capped / log / z-score) with Pearson and Spearman trend lines, plus a plain-language verdict on robustness. |
| 🕵️ **Outlier Explorer** | Leave-one-out analysis: how much does a correlation move when each country is removed? Then exclude countries yourself and watch the scatter and correlation update live. |
| 🏆 **Leaderboard** | Full ranking table for any indicator with scores and ranks under all four scalings; filter by category, search, download as CSV. |

## Concepts in the dashboard

- **Four scaling methods.** Raw values are mapped to 0–1 scores four ways so
  you can see how sensitive the rankings are to the choice. A sidebar selector
  sets the method used by the single-score pages (Country Explorer, CHIPS
  Explorer, Leaderboard and the Outlier leave-one-out); the comparator and
  correlation pages always show all four side by side:
  - *Full-range min-max* — simple, but a single extreme country can compress everyone else.
  - *5–95 percentile capped min-max* (default) — the robust choice for reporting.
  - *Log-transformed min-max* — reflects percentage-like differences, compresses the upper tail.
  - *Z-score (standardized)* — each country's distance from the mean in standard
    deviations, mapped to 0–1 via the logistic curve. Ranks match plain
    z-scores, but the values stay on the same scale as the other methods.
- **Pearson vs. Spearman.** Pearson measures linear correlation; Spearman ranks
  the data first, so it tolerates outliers. When the two disagree strongly, the
  link is driven by a few extreme countries.
- **Capped score = "goodness" (higher is better).** In comparison charts, each
  indicator is capped-scaled and inverted where a low raw value is better, so
  1.0 always means "best on this indicator".

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
- more than half of a group missing (or only 1 of 2 present) drops the group,
  and the drop propagates up one level;
- the INNOVATE → AI sub-pillar has two internal groups — the research pair
  (AI Innovation - Research + AI R&D score) and the remaining three AI
  indicators — and needs both to survive;
- CHIPS itself requires at least 3 of the 5 pillars.

Every decision is recorded per country, so the page can show *why* a score is
what it is — hover any treemap block or heatmap cell.

## Project layout

```
SIDE_dashboard/
├── dashboard.py              # entry point (streamlit run)
├── requirements.txt
├── core/                     # data + analysis logic (no UI)
│   ├── loader.py             # reads the CSV, friendly names, categories
│   ├── scaling.py            # the four 0–1 scaling methods
│   ├── rankings.py           # rank tables, stability, profile ranks
│   ├── correlations.py       # pair preparation, leave-one-out, exclusions
│   ├── chips_hierarchy.py    # CHIPS spec: pillars, sub-pillars, weights, column map
│   ├── chips.py              # CHIPS aggregation engine + missing-data rules
│   └── themes.py             # the five notebook themes + highlight countries
├── components/
│   ├── charts.py             # every plotly figure builder
│   ├── country_names.py      # ISO3 -> short/long country names
│   └── ui.py                 # streamlit helpers (selectboxes, tables, config)
├── views/                    # one module per dashboard page
└── tests/
    └── test_chips.py         # CHIPS rule + integration tests (python -m tests.test_chips)
```
