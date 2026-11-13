---
description: Audit data coverage, missing countries, and stale vintages
agent: data
---

Audit data coverage for **$ARGUMENTS** (default: every indicator in the current
edition, `DEFAULT_YEAR`).

Produce a table with one row per indicator:

| Indicator | Pillar · Sub-pillar | Countries present | Missing | Source | Latest vintage | Notes |

Rules:

- "Present" means a non-null numeric value after the standard loader pipeline,
  not merely a column that exists.
- List the missing countries by name when there are 10 or fewer; otherwise give
  the count and the most notable gaps.
- Distinguish **missing** from **stale**. If a column exists but its source year
  is older than the edition year, flag it in Notes and say how you determined
  the year.
- Do not fill, impute or "fix" anything in this command. This is an audit.
- Save the table as a CSV under `deliverables/coverage-audit/` and a short
  `findings.md` next to it.

End with the three indicators that most threaten cross-country comparability and
why.
