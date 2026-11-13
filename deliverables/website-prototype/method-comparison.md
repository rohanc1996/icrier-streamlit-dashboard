# Scaling methods — score and rank comparison

Edition **2026 Absolute**, exported from the CHIPS
engine (`SIDE_dashboard/core/chips.py`) on 2026-11-13T10:09:16Z.

`full_minmax` = full-range min–max (`scaling.METHOD_FULL`); `z` = z-score, standardised then mapped through the logistic curve (`scaling.METHOD_Z`). Both keep every country on the same 0–1 scale.

## Five countries

| Country | full_minmax score | full_minmax rank | z score | z rank | Δ score |
| --- | --- | --- | --- | --- | --- |
| India | `0.40409999999999996` | 3 | `0.6603` | 3 | +0.2562 |
| Brazil | `0.2546` | 7 | `0.5543` | 7 | +0.2997 |
| Costa Rica | `0.1892` | 41 | `0.44549999999999995` | 51 | +0.2563 |
| United States of America | `0.6727` | 1 | `0.8090999999999999` | 1 | +0.1364 |
| Singapore | `0.2531` | 8 | `0.5303` | 9 | +0.2772 |

`Δ score` is `z - full_minmax`; it shows how much the 0–1 position moves
between methods. The rank columns are the published competition ranks
(1 = best, ties share the minimum).

## Rank agreement

Ranks are compared at each level. Per-indicator ranks are expected to agree (monotone transforms); aggregate ranks are measured, not assumed. Compared: **71** countries overall, **355** country×pillar pairs, **3714** country×indicator pairs.

| Level | Compared | Disagreements | Max abs delta | Share |
| --- | --- | --- | --- | --- |
| Overall CHIPS rank | 71 | 64 | 19.0 | 64 of 71 |
| Pillar ranks | 355 | 312 | 35.0 | 312 of 355 |
| Sub-pillar ranks | 1110 | 719 | 35.0 | 719 of 1110 |
| Indicator ranks | 3714 | 0 | 0 | — |

### Largest overall movements

| Country | ISO-3 | full_minmax rank | z rank | delta |
| --- | --- | --- | --- | --- |
| Saudi Arabia | SAU | 55.0 | 36.0 | -19.0 |
| Peru | PER | 22.0 | 40.0 | +18.0 |
| Kenya | KEN | 47.0 | 60.0 | +13.0 |
| Ukraine | UKR | 50.0 | 62.0 | +12.0 |
| Philippines | PHL | 27.0 | 38.0 | +11.0 |
| South Africa | ZAF | 54.0 | 43.0 | -11.0 |

The full list of 64 movers is in `export-report.md`.

### Why composite ranks move

Within a single indicator the two scalings are monotone transforms of the same raw value, so their indicator ranks are identical (zero disagreements above). The composite CHIPS score is not a single transform: it is a weighted sum of per-indicator scores. Full-range min–max spreads each indicator linearly over its observed range, while z-score pushes values through the logistic curve, compressing both tails and pulling mid-pack countries toward 0.5. Weighted sums of two differently shaped curves therefore need not rank countries the same way.

This is engine behaviour, not an export artefact: the numbers here reproduce `SIDE_dashboard/core/rankings.py:composite_scaling_comparison` exactly (0 mismatches on all 71 overall ranks and 355 pillar ranks), and `SIDE_dashboard/tests/test_chips.py` asserts that composite ranks *can* differ between methods. Rank difference is therefore a finding for the site copy, not a bug to hide: the toggle changes the league table, not just the score column.

Pillar disagreements by pillar: CONNECT 58, HARNESS 58, INNOVATE 64, PROTECT 64, SUSTAINABILITY 68.

Indicator ranks are computed on the unrounded score matrix, which both methods transform monotonically. Of 4118 country×indicator rows per method, 3714 are ranked on both sides; the other 404 lack a raw value for that country and carry `rank: null` under both methods (the same rows in each).
