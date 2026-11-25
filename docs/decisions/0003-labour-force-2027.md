# 0003 — Labour-force denominator for the 2027 Relative series

- **Date:** 2026-11-25
- **Status:** accepted

## Context

`SIDE 2027 - Relative.csv` has **"ICT sector employment (% of Total Labour
force)"**. The numerator (`Employment: ICT sector (thousands)`) exists in the
Absolute file; the labour-force denominator was missing from
`data/denominators.csv`.

A file was supplied as `data/reference/ILO stat labour force
EAP_TEAP_SEX_AGE_NB_A-reshaped-2026-11-23.csv`, labelled as the ILO labour
force. Two problems ruled it out:

1. **Wrong ILO product.** It is `EAP_TEAP_SEX_AGE_NB_A` — ILO **national**
   estimates, i.e. each country's own survey. The 2026 edition was built from
   the ILO **modelled** series (`EAP_2EAP_SEX_AGE_NB_A`), which is what the
   World Bank republishes as `SL.TLF.TOTL.IN`, rebased onto World Bank
   population estimates. The two diverge sharply where national coverage is
   narrow: Argentina 14.5m vs 22.4m (the national series is an urban household
   survey), Singapore 2.46m vs 3.6m, India 499m vs 618m, Nigeria 99m vs 117m.
2. **Broken row alignment.** The UK row carried the USA series (2025 =
   170,807.2 = ILOSTAT USA), the USA row carried Vietnam's series, a row
   labelled Ghana under ISO `HUN` duplicated Ghana's 2017 value, and the
   Saudi row was empty. UK, USA, Hungary, Vietnam and Saudi Arabia were
   unusable.

Checked against the denominator implied by the 2026 published ratio, the World
Bank series is the right one:

| Series | median abs. error | mean | p90 | max |
|---|---:|---:|---:|---:|
| World Bank `SL.TLF.TOTL.IN` (2024) | 0.91% | 1.11% | 2.35% | 3.3% |
| ILO modelled `EAP_2EAP` (2024) | 1.50% | 1.94% | 4.15% | 8.1% |

The residual gap against raw ILO modelled is the World Bank population
rebasing, which confirms `SL.TLF.TOTL.IN` is what 2026 used.

## Decision

1. New reference snapshot: `data/reference/WB labour force by year.csv`, the
   official WDI bulk export for `SL.TLF.TOTL.IN` (same wide layout and
   `Last Updated Date` metadata as the GNI and listed-company files).
2. `build_denominators.py` adds `Labour_force_2025` (thousands) and
   `Labour_force_source_year`, reusing `load_wdi_wide()` and `value_for()`.
3. A missing 2025 falls back to the latest observation, with the year written
   to `Labour_force_source_year` — no silent carry.
4. The faulty ILO national-estimates CSV is deleted rather than kept, so it
   cannot be mistaken for the source of truth.
5. Validation asserts: 71/71 non-blank and positive; labour force between 20%
   and 80% of population (the band that catches the USA-at-16% and
   UK-at-247% errors); and exactly one carry-back, Ukraine 2021.

## Consequences

- No level break against 2026 for the ICT-employment ratio.
- Coverage is 70/71 at 2025. Ukraine is 2021 (20,538.7 thousand): WDI has no
  observation after the invasion. This is visible in the data via
  `Labour_force_source_year`, and future coverage changes fail the build.
- The ILO national-estimates series remains available upstream if a later
  edition deliberately wants a reported-not-modelled basis; that would be a
  methodology change requiring its own ADR.
- `SL.TLF.TOTL.IN` is ILO modelled estimates with World Bank population and
  staff adjustments, so any document describing this denominator should say
  "ILO modelled estimates via the World Bank", not "World Bank data" or "ILO
  national statistics".
