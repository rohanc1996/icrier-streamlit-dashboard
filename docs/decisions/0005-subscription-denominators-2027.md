# 0005 — Subscription denominators for the 2027 Relative series

- **Date:** 2026-11-25
- **Status:** accepted

## Context

Three columns of the 2026 Relative file are subscription-denominated:

- `Mobile Cellular Subscriptions per 100 population` — mobile subscriptions divided by population.
- `Mobile broadband internet traffic (GB per subscription)` — divided by mobile subscriptions.
- `Fixed-broadband Internet traffic per subscriber (GB)` — divided by **fixed-broadband** subscriptions.

`data/denominators.csv` carried neither subscription count, so the 2027
Relative file could not support those three columns. Two ITU extracts were
supplied for the 2027 edition:

- `data/reference/Mobile-cellular subscriptions.csv`
- `data/reference/Fixed-broadband subscriptions.csv`

Both are wide (one row per economy, columns `2018`–`2026`), 215 and 218
economies respectively, with blanks written as `-`. All 71 SIDE countries are
present once four ITU spellings are mapped (`Czechia ← Czech Republic`,
`Dominican Republic ← Dominican Rep.`, `Republic of Korea ← Korea (Rep. of)`,
`United States of America ← United States`). The `2026` column is empty in both
files, so neither can support a 2026 refresh.

### The mobile extract does not equal the scored indicator

`Mobile Cellular Subscriptions in millions (absolute numbers)` in
`SIDE 2027 - Absolute.csv` is **derived**, not reported:
`build_itu_csv.py` multiplies ITU's per-100 rate by UN DESA population for the
year the rate refers to. The new extract holds ITU's *reported* totals. ITU's
own rate and its own total are not always consistent, so the two series
differ:

- Reconciliation at each country's `Mobile data year` (`itu-transposed.csv`):
  **69 of 71 agree**, one of them only through ±1 round-off (Ukraine).
- **Serbia** differs by 1.9%: the scored value is 8,340,931 (per-100 rate ×
  population); the extract reports 8,178,664 for the same 2024 data year. No
  year in the extract reproduces the scored value.
- **Norway** has no 2025 value in the extract, although the indicator's data
  year is 2025.
- Three countries are on a 2024 data year (Chile, Saudi Arabia, Serbia), the
  rest on 2025.

Fixed broadband has no counterpart in the Absolute file; 2025 coverage is
68/71, and Japan (2023), Norway (2024) and the United Kingdom (2024) need a
carry-back.

### What the 2026 file was built on

Back-solving the 2026 `per 100` column against `Population_2025` shows the
published figures use **2024** subscription counts (35/59 within 1%, median
error 0.73%), not 2025. The 2026 Relative file is part of the published record
and must not be rebuilt from these extracts: its numbers would move.

## Decision

1. `build_denominators.py` adds four columns:
   `Mobile_subscriptions`, `Mobile_subscriptions_source_year`,
   `Fixed_broadband_subscriptions`,
   `Fixed_broadband_subscriptions_source_year`. Counts are raw country counts,
   matching the other count columns, not millions.
2. **Mobile uses the year the scored indicator actually uses**, taken from the
   `Mobile data year` row of `itu-transposed.csv`, not a blanket 2025. The
   value is the extract's figure for that year.
3. **Serbia is the one override:** the denominator takes the Absolute value so
   numerator and denominator cannot disagree (see
   `MOBILE_ABS_OVERRIDES`). Norway falls back to the Absolute value because the
   extract has no 2025 observation, and keeps 2025 as its source year.
4. Fixed broadband takes 2025, else the latest earlier observation, and always
   records `Fixed_broadband_subscriptions_source_year` so a carry-back is
   visible in the CSV.
5. `_validate` asserts per country: both counts are positive integers; mobile
   is 0.15–2.5 per head and fixed broadband 0.0005–0.75 per head of
   `Population_2025`; fixed never exceeds mobile; mobile differs from the
   Absolute indicator by at most one subscription, and by exactly zero for
   Serbia; the only non-2025 mobile data years are Chile, Saudi Arabia and
   Serbia (2024); the only fixed-broadband carry-backs are Japan (2023),
   Norway (2024) and the United Kingdom (2024).
6. `scripts/analysis/reconcile_subscriptions.py` keeps the reconciliation
   reproducible and writes
   `data/derived/subscription_denominator_reconciliation.csv`.

## Consequences

- Three 2027 Relative columns gain a denominator: 71/71 for mobile, 71/71 for
  fixed broadband (68 at 2025, 3 carried back).
- The mobile denominator duplicates the Absolute column to within one
  subscription by design. Any future re-pull of ITU's per-100 series that moves
  the scored value will fail the assertion rather than silently shift the
  relative series.
- **Open, and deliberately not decided here:** the per-100 ratio divides a
  count whose year can be 2024 by `Population_2025`. The ITU sheet already
  carries `UN DESA total population (mobile year)`, which would align the two;
  using it would also change the existing internet-user ratios, so it needs its
  own decision.
- **Open:** the "GB per subscription" traffic ratio divides an EB total by an
  annual subscription count with no stated period. The 2026 column medians
  3,309 GB per fixed subscription, roughly 12× a plausible monthly figure. The
  period must be stated before those 2027 columns are published.
- Adding fixed broadband as a *scored* Connect indicator is still a separate
  decision: it would change the Access sub-pillar weights (25% → 20%) and needs
  the three missing 2025 observations resolved first.
