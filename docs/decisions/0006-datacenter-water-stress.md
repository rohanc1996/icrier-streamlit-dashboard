# 0006 — Data-centre water-stress exposure in the SUSTAINABILITY pillar

- **Date:** 2026-11-27
- **Status:** proposed

## Context

The 2027 SUSTAINABILITY pillar carries six indicators: e-waste per capita, the
share of energy startups that are digital, VC investment in AI and
environmental sustainability, smart-grid patents as a share of enabling
technology, renewable energy share of electricity production, and average
annual loss from climate. None of them concerns water, even though cooling is
the physical constraint that governs where large AI campuses can be built.

Two representations were available. A **national** measure (withdrawal as a
share of renewable resources, or renewable freshwater per capita) is available
for all 71 SIDE countries from AQUASTAT/WDI and is trivial to join. A
**sub-basin** measure requires spatial work but describes the place a facility
actually sits in.

The two are not interchangeable. Across the 71 countries the sub-basin index
correlates with national water stress at only ρ = 0.56, and with per-capita
availability at ρ = −0.33. Peru and Chile look water-secure nationally (5% and
9% withdrawal-to-supply; 49,000 and 45,000 m³ per capita) while their data
centres sit in hyper-stressed coastal basins; Singapore looks absolutely scarce
per capita (106 m³) while its facilities sit in a basin that is not stressed.

## Decision

1. Use WRI Aqueduct 4.0 `baseline_annual`, at the intersection of sub-basin,
   province and aquifer, CC BY 4.0. Each facility takes the `bws_score` of the
   unit containing it.
2. The country value is the capacity-weighted mean of those scores, rescaled to
   0–100; lower is better, so the loader inverts it
   (`HIGHER_IS_BETTER = False`).
3. Weight by measured MW where Epoch AI publishes it (93 sites, 14.3 GW), and by
   a 5 MW placeholder elsewhere. A 15 MW placeholder and a network-count
   alternative are published as sensitivity columns.
4. The index is an **intensity, not a total**. Absolute exposure (`mw_high`) is
   reported alongside but does not enter the composite; otherwise the indicator
   would re-rank countries by fleet size, which CONNECT and HARNESS already
   measure.
5. Countries with fewer than three facilities are left blank rather than scored
   on thin evidence.
6. SUSTAINABILITY becomes a seven-indicator equal-weighted group (1/7 each),
   applied only when the 2027-only column is present.

## Consequences

- The pillar's weights change from six indicators at 0.17 to seven at 0.1429.
  `validate_spec_totals` stays clean because the group resolves to equal weights.
- The series is populated for 65 of 71 countries. The other six (Algeria, plus
  five with fewer than three facilities) are explicit blanks.
- **The pillar will not render a score until the other six SUSTAINABILITY
  columns are populated.** With 6 of 7 components missing the group is dropped
  by the >50%-missing rule in `core/chips.py`, which is correct behaviour but
  worth knowing before anyone reports the pillar as "broken".
- PeeringDB's AUP forbids bulk redistribution. The facility snapshot is
  gitignored; only country aggregates are committed.
- The measure is exposure, not consumption: cooling design drives actual water
  use, and the observed spread between comparable sites is roughly 20-fold.
  A future revision could weight by water use where Epoch reports it (25 of 96
  sites), but coverage is too thin for 2027.

## Alternatives rejected

- **National water availability as the indicator.** Smooths away exactly the
  hotspots the indicator exists to find (Peru, Chile, Bangladesh all fall more
  than 35 places), and rewards water-rich, sparsely populated countries
  irrespective of where the infrastructure sits. Retained as a companion
  column for context, not as the score.
- **Absolute MW in stressed basins as the score.** Ranks the United States,
  Indonesia, Germany and India at the top purely because they have the most
  facilities.
- **OSM building footprints as the facility layer.** Coverage outside Europe is
  too sparse to carry the indicator.
- **Commercial inventories (Baxtel, S&P 451).** Would replace the 5 MW
  placeholder with measured capacity for ~13,000 sites, but are paid. Worth
  revisiting if a research licence is available.
