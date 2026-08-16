# ICRIER SIDE 2026 Digital Economy Dashboard

An interactive Streamlit companion to the **SIDE 2026** digital economy dataset
(71 countries, 60+ indicators). It gives the research team a point-and-click
way to tinker with indices, compare scaling methods, explore correlations, and
see how sensitive rankings are to methodology choices — before the final report
is written up.

> ### ⚠️ Status: internal working tool — not for public distribution yet
>
> This repository (and the app it deploys) is intended for **ICRIER's research
> team and trusted collaborators while the SIDE 2026 report is in progress.**
> Nothing in here is confidential, but the data and results are **pre-publication
> and may still change**. Please don't share the repo or the deployed app link
> broadly, and don't cite or quote the numbers, until the report is published.
>
> A reader-facing version of the dashboard will be released alongside the final
> report. If you found your way here in the meantime — welcome, but please treat
> everything as a work in progress.

## What's inside

The dashboard has three active pages:

| Page | What it does |
| --- | --- |
| 🏆 **CHIPS Index Explorer** | The CHIPS composite index (CONNECT · HARNESS · INNOVATE · PROTECT · SUSTAINABILITY) with leaderboard (scrollable race chart of thin lines with flags + table), world map, per-country drill-down and full missing-data transparency. |
| 🌍 **Country Explorer** | Map any indicator, inspect a single country's profile, or compare up to five countries on a spider chart. |
| ⚖️ **Scaling Comparator** | See how the four scaling methods change rankings on any indicator. |


Currently disabled:
| 🔬 **Correlation Explorer** | Two-indicator scatter plots with Pearson/Spearman trends and a plain-language verdict. |
| 🕵️ **Outlier Explorer** | Leave-one-out analysis to find which countries drive a correlation. |

## Getting started

**Locally**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r SIDE_dashboard/requirements.txt
streamlit run SIDE_dashboard/dashboard.py
```

Your browser opens at `http://localhost:8501`.

**Streamlit Community Cloud**

This app's last commit on main is deployed at: [side2027.streamlit.app](https://side2027.streamlit.app/)


## Repository layout

```
├── SIDE_dashboard/                        # the Streamlit app
│   ├── dashboard.py                       # entry point (streamlit run)
│   ├── requirements.txt
│   ├── core/                              # data loading, scaling, CHIPS logic
│   ├── views/                             # one module per dashboard page
│   ├── components/                        # plotly charts, streamlit UI helpers
│   └── tests/                             # unit tests for the CHIPS rules
├── SIDE 2026 - Rohan - Absolute.csv       # the underlying dataset
├── skewed_column_scaling_analysis.ipynb   # the analysis notebook behind the app
└── README.md
```

## Documentation

The detailed technical README — pages, the four scaling methods, and the
complete CHIPS methodology — lives in
[`SIDE_dashboard/README.md`](SIDE_dashboard/README.md).

## Feedback

Questions or suggestions while the report is in progress? Contact the SIDE team. Please note the pre-publication guidance above when sharing anything from this repo.
