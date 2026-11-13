---
description: Add a new indicator to the SIDE 2027 dataset end-to-end
agent: data
---

Add the indicator **$ARGUMENTS** to the SIDE 2027 edition, end to end.

Work in this order and report numbers at each step:

1. **Find the source.** Look under `data/2027 individual indicators/` (and
   `data/reference/` if relevant). Read it with pandas and report: shape,
   columns, country-name style, and the exact period/vintage each column covers.
2. **Check coverage.** Match country names against the 71 SIDE countries. Report
   how many match, which are missing, and whether the indicator is available for
   all of them. If coverage is poor, stop and tell me before proceeding.
3. **Decide the treatment.** State whether higher is better, which scaling method
   applies, and whether the raw values need unit conversion. Do not invent an
   inversion.
4. **Write the data.** Add the column to the correct
   `data/2027 pillar-wise/SIDE 2027 Absolute - <Pillar>.csv` **and** to
   `data/SIDE 2027 - Absolute.csv`, keeping the two in sync. Preserve source
   precision and the existing CSV conventions.
5. **Wire the framework.** Add it to `core/chips_hierarchy.py` under the
   2027-only extension with the correct pillar/sub-pillar and weight. Do not
   change the pre-2027 spec, and keep every level summing to 100%.
6. **Verify the dashboard.** Confirm the loader resolves the column and the
   CHIPS table includes it for 2027 only. Check 2024–2026 scores are unchanged.
7. **Run the tests.** `cd SIDE_dashboard && ../.venv/bin/python -m tests.test_chips`
   plus `./.venv/bin/python scripts/tests/frozen_years.py`.

If the source, pillar, or weight is ambiguous, ask before writing anything.
Finish with a short table: countries covered, missing countries, any rank changes
it causes.
