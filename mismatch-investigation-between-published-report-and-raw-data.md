# CHIPS mismatch investigation: published report vs dashboard raw data

Reconciliation of the dashboard's **CHIPS** scores against the scores published
in last year's SIDE 2026 report, for both the **Absolute** and **Relative**
variants of the index. The two analyses share the same scripts
(`scripts/reconcile_chips.py`, `scripts/divergence_detail.py`, unchanged code)
and the same methodology; they differ in the base dataset and in the set of
data/rule corrections each required.

## Common methodology

- Published source: `data/SIDE 2026 - AI augmented {Absolute|Relative} Index
  2026.csv` (CHIPS score line 96).
- Dashboard source: `data/SIDE 2026 - {Absolute|Relative}.csv`, full-range
  min-max, with the dataset's columns mapped onto the canonical CHIPS
  indicator set.
- 71 countries reconciled in each run; a country matches when its score is
  within 0.1 points of the published value.
- Remaining gaps are classified by root cause:
  - **ROUNDING-ONLY** — agree within tolerance (rounding noise);
  - **AGGREGATION / WEIGHTS** — structural difference in how a sub-pillar /
    subgroup is aggregated or weighted;
  - **INDICATOR (data-version / min-max bound)** — a data-value or bound
    difference on a specific indicator.

---

# Part 1 — Absolute reconciliation: AI subgroup "keep-if-any" rule

Run with `--data-file "data/SIDE 2026 - Absolute.csv"` after changing the
INNOVATE · AI missing-data rule. Decimal columns were used throughout.

## Rule change

Previously a subgroup of the INNOVATE · AI sub-pillar was dropped when more than
half its indicators were missing (the generic >50% rule): the 3-indicator
*Investment & commercial* group was dropped whenever only 1 of its 3 indicators
was present (in practice almost every country only has `AI commercial`).

New rule (matching the published spreadsheet, which scores each subgroup from
whatever indicators are present): **an AI subgroup is dropped only when it has
no data at all.** If even 1 indicator is present the subgroup survives and that
member is weighed in full. Implemented in `core/chips.py` via `keep_if_any`,
applied only to the internal groups of the non-flat AI sub-pillar (`is_ai`).

## Summary

- 71 countries reconciled; **68 match to within 0.1 points** (42 exactly, to
  2 dp).

| Root cause | Countries |
|---|---|
| ROUNDING-ONLY | 68 |
| AGGREGATION / WEIGHTS | 2 |
| INDICATOR (data-version / minmax bound) | 1 |

## What the rule change resolved

The AI-subgroup drop was the dominant source of the residual mismatch. After the
change, 25 countries' dashboard CHIPS move (largest: Croatia +0.58) and the
following were pushed below the 0.1-point threshold and re-classified from
AGGREGATION / WEIGHTS to ROUNDING-ONLY:

Croatia (0.58 → 0.00), Chile (0.20 → 0.01), Indonesia (0.13 → 0.01), Kenya
(0.12 → 0.00), Hungary (0.12 → 0.00), Qatar (0.11 → 0.01), Russian Federation
(0.10 → 0.01). Rwanda, Greece, Sri Lanka, Slovakia also tightened.

## Remaining divergences (3 of 71)

### AGGREGATION / WEIGHTS
- **Bangladesh** (1.24): published SUSTAINABILITY = 49.1 vs dashboard 39.3. The
  published report does not link the sustainability patent indicator into its
  score; the dashboard does (a deliberate dashboard correction). Also carries a
  small INNOVATE · AI residual.
- **Switzerland** (0.29): published INNOVATE · AI = 12.0 vs dashboard 8.5. Both
  of Switzerland's AI subgroups are already fully present, so this is a genuine
  flat-weighting-vs-two-group weighting difference, not a missing-data effect —
  it is unaffected by the rule change.

### INDICATOR (data-version / minmax bound)
- **Italy** (0.96): published Fixed broadband price = 11.9 (implies raw ≈ 132);
  dashboard raw = 46 → 73.0. This is the published report's mistyped price; the
  dashboard keeps the corrected raw value of 46.

## Comparison with previous runs

| | rounded file | decimals (old AI rule) | decimals (keep-if-any) |
|---|---|---|---|
| exact matches (2 dp) | 12 | 28 | 42 |
| within 0.1 pts | 62 | 61 | 68 |
| INDICATOR root cause | 3 | 1 | 1 |
| AGGREGATION / WEIGHTS | 6 | 9 | 2 |

The combination of decimal columns + the AI "keep-if-any" rule leaves only three
genuine, explainable gaps: Bangladesh (published patent not linked), Switzerland
(AI weighting structure), Italy (published broadband typo).

---

# Part 2 — Relative reconciliation: Ransomware + AI-users data fixes

Re-analysis of the dashboard's **Relative** CHIPS output against the scores
published in the report, re-run after two rounds of corrections to the
underlying Relative raw data:

1. **Ransomware-attacks column** restored to full precision (previously rounded
   to 2 dp, near-degenerate).
2. **Number of AI users** column now carries true decimal values (it is a
   % of the total population; previously stored as integers).

- Dashboard source: `data/SIDE 2026 - Relative.csv` (analysed from the
  corrected working copy `data/SIDE 2026 - Rohan - Relative.csv`), full-range
  min-max, Relative columns mapped onto the canonical CHIPS indicator set.

## Summary

- 71 countries reconciled; **65 match to within 0.1 points** (7 exactly).
- Only **4 real divergences** remain among countries with a published score
  (largest: Italy 1.36, Switzerland 1.16, Uzbekistan 0.68, South Africa 0.22).
- 2 countries (Dominican Republic, Kuwait) still have no published CHIPS score
  but do on the dashboard — counted as diverging.

| Root cause | Countries |
|---|---|
| ROUNDING-ONLY | 65 |
| AGGREGATION / WEIGHTS | 4 |
| INDICATOR (data-version / min-max bound) | 2 |

## Both data fixes are confirmed working

- **Ransomware attacks (30-day average)** — no longer flagged for any country.
  The dashboard's full-minmax score reproduces the published Relative
  Ransomware row almost exactly for every country (rank correlation ≈ 1.0,
  max gap ≈ 0.005 points). Before the fix this single indicator explained 25 of
  28 divergences (e.g. Italy 75.8 vs 100.0, Switzerland 36.3 vs 0.0).
- **% of population that are using AI** (CONNECT · AI, raw column *Number of AI
  users*) — the previous 0.5–1.2-pt bound drift on this indicator is gone; the
  dashboard now matches the published row within ≈ 0.005 points for all 68
  comparable countries. This removes the last contributor to the *Italy* and
  *Switzerland* flags from the earlier round.

## What the remaining divergence is driven by

- **Italy (1.36)** — CONNECT · Affordability: *Fixed (broadband) internet price,
  USD PPP* published 11.9 vs dashboard 97.0. The same known published
  broadband-data version issue seen in the Absolute reconciliation; the %-AI
  contributor is now resolved, leaving this as the sole cause.
- **Switzerland (1.16)** — purely structural: the INNOVATE · AI sub-pillar
  scores 31.8 published vs 18.4 dashboard. The dashboard aggregates that
  sub-pillar through two internal groups (research pair ½ + investment /
  commercial ½) while the published sheet uses a flat weighting. No data gap.
- **Uzbekistan (0.68)** — SUSTAINABILITY · Sustainability sub-pillar aggregates
  to 37.76 on the dashboard vs 32.2 published while every shared indicator
  reconciles individually (composition / weighting residual; the published VC
  cell for Uzbekistan is blank per the earlier linking-error note).
- **South Africa (0.22)** — *Renewable energy share of electricity
  production (%)*: dashboard 8.1 vs published −0.2. The −0.2 was a typo in the
  published source data (correct value 8.30%); once the published sheet is
  re-exported with that cell corrected the gap should disappear. The published
  CSV being compared still holds −0.20 (see manual notes below).
- **Dominican Republic / Kuwait** — no published CHIPS score to compare
  against; the dashboard scores them (CHIPS 32.4 → rank 35 and 47.3 → rank 3).

## Comparison across rounds

| | Relative (pre-fix) | + Ransomware fix | + AI-users fix (now) | Absolute |
|---|---|---|---|---|
| within 0.1 pts | 42 / 71 | 65 / 71 | 65 / 71 | 68 / 71 |
| exact matches | 3 | 8 | 7 | 42 |
| divergent (>0.1, real scores) | 27 | 4 | 4 | 3 |
| largest gap | Italy 1.71 | Italy 1.37 | Italy 1.36 | — |
| ransomware-driven flags | 25 of 28 | 0 | 0 | 0 |
| %-AI-users-driven flags | 13 | 2 (Italy, Switzerland) | 0 | 0 |

---

# Cross-index conclusions

The Relative dashboard now agrees with the published Relative index almost as
closely as the Absolute dashboard did with the published Absolute index. Every
remaining divergence in either variant traces back to a known published-data
issue (Italy broadband typo, South-Africa renewables typo), a structural
weighting difference (Switzerland INNOVATE · AI; Uzbekistan Sustainability;
Bangladesh patent not linked in the published sheet), or a country the
published sheet does not score (Dominican Republic, Kuwait) — **none trace back
to the dashboard raw data.**

## Shared / recurring root causes across both indexes

- **Italy — *Fixed (broadband) internet price, USD PPP* (CONNECT ·
  Affordability)**: the published report's mistyped price (11.9, implies raw
  ≈ 132) vs the dashboard's corrected raw value (46). Affects both the Absolute
  (0.96) and Relative (1.36) reconciliations.
- **Switzerland — INNOVATE · AI sub-pillar**: the dashboard aggregates through
  two internal groups (research pair ½ + investment / commercial ½) while the
  published sheet uses a flat weighting. Affects both the Absolute (0.29) and
  Relative (1.16) reconciliations; in both cases it is structural (no data
  gap).

## Files

- `reconciliation_71.csv` — all 71 countries, sorted by absolute difference.
- `first_divergence_by_country.csv` — affected countries with first divergent layer.
- `root_cause_groups.csv` — grouped by root cause.
- `divergences_detail.csv` — per-country, per-layer divergence detail.

---

# Manual notes / data corrections (Relative run)

- The Excel sheet rounds to 2 decimal places, so the small ransomware-attacks
  values weren't showing up in the dashboard Relative file. Fixed (full
  precision restored) — this is why the pre-fix analysis attributed 25 of 28
  divergences to Ransomware attacks.
- The dashboard Relative file's *Number of AI users* column is a % of the total
  population and was stored as integers; it now carries true decimals (e.g.
  Germany 29 → 28.6, Singapore 61 → 60.9). This closes the last %-AI bound
  drift for Italy and Switzerland.
- Uzbekistan does have the 'Renewable energy share of electricity production
  (%)' in published and raw. South Africa's was missing in the dashboard file
  and has since been added. The other renewable-data column is not used.
- Uzbekistan's VC investments in AI and sustainable-tech score was a linking
  error; it should be blank (and is blank in the published file).
- For South Africa, the published data had a typo under Renewable Energy share
  (−0.2%). The correct value is 8.30%. It still appears as −0.20 in the
  published CSV export compared here, so South Africa remains flagged (0.22) until
  that sheet is corrected and re-exported.
- The analysis ran against the dashboard's expected filename
  (`data/SIDE 2026 - Relative.csv`); the corrected working copy is currently
  named `data/SIDE 2026 - Rohan - Relative.csv`, which the loader would not
  recognise as the Relative dataset, so it was temporarily placed at the
  canonical path for the run and removed afterwards.
