# SIDE 2026 — Published Report: Errors to Disclose in the Next Publication

This file records the known errors and methodology disclosures that should be
acknowledged in ICRIER's next SIDE publication. It is based on the CHIPS
reconciliation work in `mismatch-investigation-between-published-report-and-raw-data.md`
and the two investigation `findings.md` files.

## 1. Confirmed errors in the published 2026 report

- **Italy — "Fixed (broadband) internet price, USD PPP" (CONNECT · Affordability):**
  the published value is **11.9**, which implies a raw value of ≈132; the correct
  raw value is **46**. This is a published mistyped price and drives the Italy
  CHIPS gap in both variants (Absolute 0.96, Relative 1.36).
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:81-83,190-193`;
  `absolute min-max values mismatch investigation/findings.md:55-58`;
  `relative min-max values mismatch re-analysis (ransomware fix)/findings.md:51-54`.*

- **South Africa — "Renewable energy share of electricity production (%)" (SUSTAINABILITY):** 
  the published value is **−0.20%**; the correct value is
  **8.30%**. This typo drives a Relative CHIPS gap of 0.22 and remains until the
  published sheet is corrected and re-exported.
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:156-160,224-227`;
  `relative min-max values mismatch re-analysis (ransomware fix)/findings.md:63-67,111-114`.*

- **Bangladesh — sustainability patent indicator:** 
  the published score does not link the sustainability patent indicator into SUSTAINABILITY, producing
  **49.1** instead of the dashboard's **39.3** (Absolute gap 1.24). This is an
  omission in the published score construction.
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:71-73`;
  `absolute min-max values mismatch investigation/findings.md:45-48`.*

- **Uzbekistan — "VC investments in AI and environmental sustainability by country (USD million)" (SUSTAINABILITY):** 
  the published cell (**4.80**) was a linking error and should be blank. The repo's reference copy has since been
  blanked; confirm whether the printed report carried the erroneous value before
  finalising the wording of the disclosure.
  *Sources: `relative min-max values mismatch re-analysis (ransomware fix)/findings_old.md:25-26,102`;
  `mismatch-investigation-between-published-report-and-raw-data.md:154-155,222-223`.*

- **"Number of AI users" — population denominator error:** 
  the percentages obtained from the data source were multiplied by **total population** figures
  rather than **working-age population** figures. This overstates the absolute
  number of AI users and any indicator or score built on that count.
  *Sources: 'eye-test' during the data collection for 2027 and comparison with the previous year.*

## 2. Methodology and coverage disclosures

- **Switzerland — INNOVATE · AI sub-pillar weighting:** the published report uses
  a flat weighting across the AI subgroup, while the dashboard aggregates through
  two internal groups (research pair ½ + investment/commercial ½). The published
  score is **12.0 vs 8.5** (Absolute) and **31.8 vs 18.4** (Relative). This is a
  structural weighting difference, not a data error, but it should be disclosed
  as a methodological inconsistency between the report and the dashboard.
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:75-78,148-151,194-198`.*

- **Dominican Republic and Kuwait — missing published CHIPS scores:** neither
  country has a published CHIPS score, but the dashboard scores them
  (CHIPS 32.4 → rank 35 and 47.3 → rank 3). Acknowledge this coverage gap in the
  next publication.
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:161-162`;
  `relative min-max values mismatch re-analysis (ransomware fix)/findings.md:68-69`.*

## Appendix: Dashboard-only fixes (not published-report errors)

These were corrected in the dashboard/repository and are recorded here for audit
purposes only; they should not be framed as errors in the published report.

- **Ransomware attacks (30-day average):** the Relative input column had been
  rounded to 2 decimal places, making it near-degenerate and causing 25 of 28
  pre-fix divergences. Full precision has been restored.
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:211-214`;
  `relative min-max values mismatch re-analysis (ransomware fix)/findings.md:97-101`.*

- **Number of AI users (integer storage):** the Relative column is a percentage of
  the population and had been stored as integers (e.g. Germany 29 → 28.6,
  Singapore 61 → 60.9). It now carries true decimals. This is separate from the
  denominator error described in Section 1.
  *Sources: `mismatch-investigation-between-published-report-and-raw-data.md:215-218`;
  `relative min-max values mismatch re-analysis (ransomware fix)/findings.md:102-105`.*
