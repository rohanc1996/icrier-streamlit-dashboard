# 0002 — Index-type indicators are exempt from percentile capping

- **Date:** 2026-11-25
- **Status:** proposed

## Context

SIDE pulls 12 of its 58 CHIPS indicators (14 of 62 in 2027) directly from third-party indices and composite scores. Together they carry **18.7% of the 2026 CHIPS weight and 19.2% of the 2027 weight**. The question was whether a SIDE-level 5th/95th-percentile cap would “double-cap” distributions that the provider had already winsorized.

It would not, literally: **none of the providers winsorizes at 5/95, or at any percentile.** But most of these indicators are already ranked, min–maxed or bounded 0–100 by the provider, so a second percentile cap would compress an already-compressed distribution and discard genuine top/bottom variance. The production dashboard also does no capping today — `core/scaling.py` implements full min–max and z‑score only. The 5–95% “capped min–max” exists only in `skewed_column_scaling_analysis.ipynb`; the winsorization actually implemented in this repo belongs to the separate WIPO GII replication (`scripts/wipo_pretreatment_analysis.py`), not SIDE.

## Decision

**Do not apply percentile capping or winsorization to an indicator that is itself a published index or composite score.** Apply winsorization, if adopted, only to raw variables. Index-type indicators keep their provider scale, or are re-scaled without a percentile clip.

The indicators covered by this rule, by provider:

| Provider | SIDE columns | Native transform | Provider caps? |
|---|---|---|---|
| Tortoise/Observer Global AI Index | AI Infrastructure (Tortoise), AI Innovation - Research, AI commercial, Development: Open Source models, AI Talent Pillar, AI Human Capital, Public trust score | Sub-pillar/overall scores rescaled 100-to-minimum; category scores 0–100 | No |
| Oxford Insights GARI | Compute capacity (Govt readiness); Safety and security | Min–max to 0–100; log transform if \|skew\|>2.0 and kurtosis>3.5 (continuous indicators only) | No |
| Stanford HAI Global AI Vibrancy Tool | AI Research and Development score; AI Skilled population (Relative AI Skill Penetration) | Min–max to [0,100] | No |
| ODIN / Open Data Watch | Open Data score | Rubric elements 1/0.5/0 → category and overall 0–100; no cross-country distribution step | No |
| Chainalysis | Crypto Index Score | Country ranks on four sub-indices → geometric mean → normalise 0–1 | No |
| National Cyber Security Index (eGA) | NCSI Index Score (2027 only) | Sum of indicator points ÷ maximum → 0–100 | No |

## Consequences

- **Protects variance.** The top and bottom of each provider distribution remain visible. This matters most for Tortoise, whose 100-to-minimum rescale deliberately preserves the full spread, and for Oxford’s Safety and security dimension, which is a three-item categorical composite (0/50/100, 0/50/100, 0/100) where a percentile cap would tie or clip whole groups of countries.
- **Raw and index indicators are treated differently.** The scaling method must know which columns are index-type. Maintain the list above in one place rather than inferring it from column names.
- **No change to current output.** The dashboard already uses full min–max or z‑score. This decision constrains only a future capped method.
- **Enforcement.** `SIDE_dashboard/core/scaling.py` (`full_minmax`, `z_score`) is the place to add an exemption set and a test that no index-type column is clipped. Reference: `SIDE_dashboard/core/chips_hierarchy.py` for the indicator list; `data/SIDE 2026 - Absolute.csv` and `data/SIDE 2027 - Absolute.csv` for the columns.
- **Sources resolved.** Safety and security is the Oxford GARI Resilience → Safety and security dimension (5% of GARI). Public trust score is Tortoise GAII Operating Environment → Public attitudes towards AI (3% of GAII). Neither provider documents winsorization.
