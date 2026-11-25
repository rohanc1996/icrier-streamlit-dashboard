# 0002 — Adding the Tracxn startup count to the denominators table

- **Date:** 2026-11-25
- **Status:** accepted

## Context

The 2027 Relative series has the indicator **"Total funding till date of
Startups … per startup (Millions of USD)"**. Its numerator already exists in
`SIDE 2027 - Absolute.csv`; the denominator — the startup count — was not in
`data/denominators.csv`.

`data/reference/tracxn startups counts.csv` supplies a 71-country Tracxn
snapshot. Two properties of the file matter:

1. **It is the same series as the absolute numerator.** All 71 values equal the
   `Number of Start-ups` column in `SIDE 2027 - Absolute.csv` exactly. The
   startup count is therefore both the numerator of "Start-ups per limited
   liability company" and the denominator of "funding per startup".
2. **The header repeats `Country`** (`Country,Country,Total Number of Startups
   (tracxn)`), so a `DictReader` keeps only the last `Country` column and loses
   the canonical SIDE name. The file must be read positionally.

The file carries no as-of date. The 2026 edition implies smaller counts than
this snapshot for most countries (US 1.40m vs 2.04m, India 649k vs 812k,
Germany 648k vs 725k, UK 1.19m vs 1.28m) — i.e. the 2027 edition uses a newer
and larger Tracxn extraction, consistent with the 2027 absolute column.

## Decision

1. Add `Startups_tracxn` to `data/denominators.csv`, built by
   `scripts/build_denominators.py` from
   `data/reference/tracxn startups counts.csv` (column 0 = SIDE country,
   column 2 = count).
2. Copy the value verbatim; do not derive, smooth or annualise it.
3. `build_denominators.py::_validate` asserts that every count is a positive
   integer **and equals the `Number of Start-ups` value in
   `SIDE 2027 - Absolute.csv`**. This pins the relative denominator to the
   absolute numerator so the two cannot drift if one is updated without the
   other.
4. The source reference CSV is not modified.

## Consequences

- The 2027 "funding per startup" ratio is reproducible from
  `data/denominators.csv` plus the absolute numerator.
- Because the 2027 startup counts are larger than those implied by the 2026
  ratio, funding-per-startup will step **down** for most countries versus 2026.
  That is a vintage change, not an error, and should be described as such.
- The extraction date is unknown. If the SIDE team supplies one, record it in a
  `Startups_tracxn_asof` column, mirroring `Listed_companies_source_year`.
- No scoring logic changes, so the CHIPS method tests are unaffected; the
  frozen-edition regression check is still run.
