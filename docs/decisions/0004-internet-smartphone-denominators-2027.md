# 0004 — Internet-user and smartphone-user denominators for the 2027 Relative series

- **Date:** 2026-11-25
- **Status:** accepted

## Context

The 2027 Relative headers declare 15 columns as "% of internet users" or "per
internet user", and two as "per smartphone user" (AR/VR and Metaverse revenue).
Neither count was in `data/denominators.csv`, so the table could not support
those columns even though both counts exist in the Absolute file.

The 2026 Relative file shows what the denominators are:

- The five "% of internet users" columns (food delivery, digital health,
  e-commerce, video on demand, users of digital payments) divide by exactly
  the `Number of Internet Users (absolute numbers)` column of
  `SIDE 2026 - Absolute.csv`. Back-solving the denominator gives a ratio of
  1.0000 to that column for all 71 countries (CV ≤ 2e-4).
- The two "per smartphone user" columns divide by
  `Number of smartphone users (million)` and then apply a country PPP factor.
  The United States reproduces exactly (12,600m USD / 287m users = 43.9, the
  relative value); the residual for other countries rises with income gap and
  is shared, to about 1%, with the other five PPP-adjusted columns.

Two traps:

1. `Number of smartphone users (million)` is **mislabelled** — it holds raw
   counts (India 816.6m, USA 235.5m in 2027), not millions.
2. One internet-user column (*Number of internet users (16-64 years) using
   social media for work related activities*) divides by internet users aged
   16–64, not total internet users. The implied denominator is ~0.84 × total
   internet users with an 8% spread. That series does not exist in the repo.

## Decision

1. `build_denominators.py` copies `Internet_users_2025` and
   `Smartphone_users_2025` verbatim from the corresponding columns of
   `data/SIDE 2027 - Absolute.csv`. No other source is introduced.
2. Values are written as raw country counts (no thousands scaling), matching
   the source columns and the units the ratios use.
3. `_validate` asserts, per country: both counts are positive integers; they
   equal the Absolute-file cells exactly (so absolute and relative cannot
   drift); internet users are 10–102% of population; smartphone users are
   25–110% of internet users (Ethiopia is the only country above 100%, at
   100.5%).
4. The 16–64 internet-user denominator is **not** added. The social-media
   column stays unbuildable until that series is sourced; it must not be
   silently approximated with total internet users.
5. The PPP factor for the seven PPP-adjusted columns (AR/VR, Metaverse, app
   spend, digital-payment value, IoT, DeFi, cybersecurity) is **not** added
   here. It is a separate denominator and needs its own decision.

## Consequences

- 15 relative columns gain a usable denominator; 2 more gain the count but
  still need the PPP factor.
- The denominator table now duplicates two Absolute columns by design, so the
  relative series cannot silently use a different user count.
- Anyone reading the CSV must treat `Smartphone_users_2025` as a count, not
  millions, despite the source column name.
- Coverage is 71/71 for both counts, with no carry-backs.
