# Data-centre water-stress exposure (0–100) — method note

Indicator for the 2027 SIDE edition, SUSTAINABILITY pillar. Prototype status:
the series is built and wired into the framework, but the pillar will not
display a score until the other six SUSTAINABILITY indicators carry values in
`data/SIDE 2027 - Absolute.csv` (they are currently blank, so the group is
dropped by the >50%-missing rule in `core/chips.py`).

## What it measures

Given the digital infrastructure a country has, how badly is it sited with
respect to water? Each facility inherits the baseline water-stress score of the
Aqueduct 4.0 sub-basin it occupies; the country value is the capacity-weighted
mean of those scores, rescaled to 0–100. Lower is better.

It is an **intensity**, not a total. we measure where capacity sits, not how much 
of it a country has: a 1 GW campus in a dry basin weighs far more than a small data 
center in a wet one, but a country with three facilities is scored on the same 
0–100 scale as one with three hundred. Absolute
exposure is reported separately (`mw_high`, `share_mw_high_pct`) and does not
enter the composite — see `docs/decisions/0006-datacenter-water-stress.md`.

## Sources

| Layer | Source | Licence | Vintage |
|---|---|---|---|
| Water stress | WRI Aqueduct 4.0, `baseline_annual` | CC BY 4.0 | baseline 1979–2019, released 2023 |
| Facilities | PeeringDB `/api/fac` | research use; no bulk redistribution | snapshot 2026-11-27, 5,912 records |
| Measured capacity | Epoch AI, *AI data centers* | CC BY 4.0 | 96 sites, 14.3 GW |

Aqueduct was chosen over FAO AQUASTAT (country-level only, cannot be
intersected with a point) and Copernicus GDO (drought timing, not scarcity)
because it is sub-basin resolution, CC BY, and every unit already carries an
ISO-3 code.

## Scoring

1. Point-in-polygon join of facilities to Aqueduct units. 5,376 of 5,399
   located facilities matched (99.6%); the rest are offshore or badly geocoded.
2. Each facility takes `bws_score` (0–5), Aqueduct's quantile-mapped version of
   the withdrawal-to-supply ratio: under 10% ≈ 0, above 80% ≈ 5.
3. Country score = `100 × Σ(wᵢ · bws_scoreᵢ) / Σ wᵢ / 5`.
4. Weights: measured MW for Epoch sites; a 5 MW placeholder for every other
   facility.
5. Minimum three facilities. Below that the score is left blank: Algeria (none)
   and Ethiopia, Iraq, Kuwait, Morocco, Sri Lanka (one or two).

## Robustness

| Variant | Column | Rank/level agreement with headline |
|---|---|---|
| 15 MW placeholder | `score_kappa15` | r = 1.000 |
| Network count (capped 50) as weight | `score_netcount` | r ≥ 0.99 |
| Every facility weighted once | `score_unweighted` | r = 0.998 |

The weighting assumption does not drive the result, because a country's
facilities usually fall in one or two basins.

## Output columns

### `data/2027 individual indicators/datacenter_water_stress.csv`

The series that enters the framework: one row per SIDE country, 71 rows.

| Column | Meaning |
|---|---|
| `Country` | Canonical SIDE country name, aligned to `SIDE 2027 - Absolute.csv` |
| `Data-centre water-stress exposure (0-100)` | Headline score, rounded to 1 decimal, lower is better. Blank where fewer than three facilities were matched (six countries) |

### `deliverables/water-stress-2027/country_table.csv`

The audit trail behind the series: one row per SIDE country, all diagnostics
included. Nothing here enters the composite except `score`.

| Column | Meaning |
|---|---|
| `Country` | Canonical SIDE country name |
| `iso3` | ISO-3166 alpha-3 code, the join key to the facility layers |
| `n_facilities` | Facilities matched to an Aqueduct sub-basin (PeeringDB plus located Epoch sites). Blank for Algeria, which has no records |
| `n_high` | Facilities in Aqueduct bands 3–4, i.e. withdrawals above 40% of renewable supply |
| `n_eh` | Facilities in band 4, above 80% — the "extremely high" category |
| `mean_bws_score` | Unweighted mean of the Aqueduct 0–5 score. The raw signal before any weighting |
| `score` | **Headline.** Capacity-weighted mean score × 20, with measured MW and a 5 MW placeholder; 1 decimal; blank where `n_facilities` < 3 |
| `score_kappa15` | Same construction with a 15 MW placeholder. Shows the score's sensitivity to the size assumption for unmeasured facilities |
| `score_netcount` | Same construction weighting every facility by `min(net_count, 50)` instead of a placeholder — the alternative if connectivity is preferred to a flat MW assumption |
| `score_unweighted` | Every facility counted once, regardless of size. The lower bound of the weighting assumption |
| `mw_total` | Measured Epoch MW in the country. Populated for the 12 countries with located Epoch sites; zero where a tracked site reports no power; blank means no measured capacity at all, not zero capacity |
| `mw_high` | Of `mw_total`, MW in basins above 40%. The absolute exposure figure quoted in the narrative |
| `share_mw_high_pct` | `mw_high` as a percentage of `mw_total`. Blank where measured capacity is zero (Sweden, UAE) or absent |
| `coarse_geocode_mw` | MW contributed by sites geocoded to a city or placed manually. An accuracy flag: high values mean the score rests on coarser coordinates |
| `flag_min_n` | `True` where `n_facilities` < 3, the rule that blanks `score`. Blank for Algeria, which has no facility records at all |

Missing values are blank, never zero. A blank `score` means "not enough
evidence", and a blank `mw_total` means "no measured capacity", not "no data
centres".

## Known limits

- **Undercount.** China shows 27 facilities; Algeria none. PeeringDB documents
  interconnection, not buildings, and self-built hyperscale campuses are often
  absent. 36% of tracked Epoch MW has no PeeringDB facility within 30 km.
- **Proxy weights.** 93 of 5,399 facilities have measured power.
- **Geocoding.** 42 sites are at street address, 51 at city or coarser, 3
  unresolved. `data/reference/epoch_sites_geocoded.csv` is the reviewable
  fixture.
- **Aqueduct vintage.** Baseline 1979–2019 is a long-run average, not current
  conditions. The 2030 BAU projection is the obvious publication variant.
- **Not water consumption.** Cooling design drives actual use; observed spread
  between comparable sites is ~20×.

## Reproducing

```bash
./.venv/bin/python scripts/data_sources/wri_aqueduct/fetch_aqueduct.py
./.venv/bin/python scripts/data_sources/datacenters/fetch_peeringdb.py
./.venv/bin/python scripts/data_sources/datacenters/fetch_epoch.py
./.venv/bin/python scripts/data_sources/datacenters/spatial_join.py
./.venv/bin/python scripts/analysis/datacenter_water_stress.py
./.venv/bin/python scripts/build_2027_absolute.py
```

Large raw downloads land in `data/derived/water_stress/raw/`, which is
gitignored. The PeeringDB snapshot must not be committed: its AUP forbids bulk
redistribution, so only the country aggregates enter the repository.
