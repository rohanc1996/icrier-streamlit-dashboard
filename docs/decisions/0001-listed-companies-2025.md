# 0001 — Filling 2025 listed-company counts for the Relative series

- **Date:** 2026-11-25
- **Status:** accepted

## Context

`data/reference/WB listed company counts by year.csv` (WDI `CM.MKT.LDOM.NO`,
listed domestic companies, total) is the source for the `Listed_companies`
denominator of the 2027 Relative series. `build_denominators.py` currently
leaves the column blank when WDI has no 2025 value: 25 of the 71 SIDE
countries, of which 6 have never reported and 19 have a stale latest
observation.

The stale group is not uniform. Six countries are 1–4 years stale (Israel 2024;
Mexico, Russia 2023; UK, Costa Rica 2022; Argentina 2021) and thirteen are 5–25
years stale (France, Ireland, Netherlands, Portugal, Ukraine 2018; Norway 2017;
Belgium 2015; Italy 2014; Slovakia 2013; Denmark, Finland 2004; Sweden 2002;
Ecuador 2000).

We need 2025 values for the Relative series without overwriting the verbatim
WDI extract or pretending an estimate is an observation.

## Decision

1. Never write estimates into the WDI reference CSV. It is a dated source
   snapshot and the provenance for the whole series.
2. Produce `data/derived/listed_companies_2025_estimates.csv`, one row per SIDE
   country, carrying `Method`, `Source_year` and `Confidence` alongside the
   value. Methods are `reported`, `exchange`, `carry_forward` and `missing`.
3. **Precedence: reported → exchange lookup → carry forward → missing.** A
   verified exchange/regulator/WFE figure is preferred at any gap; carry
   forward is only a fallback when no observation exists and the gap is 1–4
   years. Never extrapolate a trend.
4. Look up every stale country, not just the long-gap ones, and record what is
   found — including a definition caveat or a blank — in
   `data/derived/listed_companies_2025_exchange_lookups.csv`. All six 1–4 year
   countries turned out to have a verifiable figure, so **no carry-forward is
   used in 2025**; the rule remains for future gaps.
5. Leave the six never-reporting countries blank. They have no series to carry
   and no comparable exchange figure.
6. `build_denominators.py` reads the estimates file and passes `Method`
   through to `data/denominators.csv`, so downstream code can restrict itself
   to `Method == "reported"` if it ever needs observed values only.
7. Re-run the pipeline when WDI publishes a genuine 2025 observation: the
   `reported` branch takes precedence, so real data replaces an estimate with
   no manual step.

**The WDI series is the WFE domestic series.** This is checkable, and it
decides which exchange figures are comparable: WDI UK 2022 = 1,606 equals the
WFE domestic count exactly, and WDI Israel 2022 = 518 equals WFE domestic
exactly. So an exchange's headline "companies traded" is usually too wide —
TASE's 546 includes 49 dual listings, LSE's 907 is "companies and funds, all
listings". Where WFE publishes a country row (Israel, Mexico) the lookup uses
it. Where it publishes only a combined line (Euronext, Nasdaq Nordic and
Baltics) the exchange headline is used and the definitional drift is recorded.

The UK needed a construction because LSE stopped reporting to WFE after January
2023, which is why the WDI series ends in 2022. The lookup is 669 domestic Main
Market + 530 domestic AIM = 1,199, mirroring how WFE built the 2022 value. It
is derived, not exchange-published, and is flagged low confidence.

**Why carry-forward and not trend for the fallback.** The backtest in
`scripts/analysis/backtest_listed_companies.py` (output:
`deliverables/listed-companies-2025/backtest.md`) predicts each country-year
from observations up to *t − h* over all 71 countries. Carry-forward has lower
median absolute error than a log-linear trend at every horizon tested:

| gap | carry-forward | trend (8-pt) |
|---:|---:|---:|
| 1 year | 3.6% | 7.0% |
| 2 years | 7.0% | 10.8% |
| 3 years | 10.1% | 14.4% |
| 4 years | 13.1% | 17.8% |

At 23–25 years the trend method's 90th-percentile error exceeds 2,600% — France
projects to 176,191 companies from its 1998 level, the Netherlands to 10,438
from 2000 — which is why long gaps never get a projection. Carry-forward does
develop a downward bias over long gaps (mean `log(pred/actual)` −16.7% at 10
years, −30% at 20), consistent with net delisting in most markets, so it is
limited to 1–4 years.

## Consequences

- The Relative series gets 2025 denominators for 14 of the 19 stale countries,
  all from exchange/WFE/regulator sources. Belgium, Ecuador, the Netherlands,
  Portugal and Ukraine remain blank because no figure with a comparable
  definition could be verified: Belgium's FSMA publishes 154 supervised
  *issuers* (shares or bonds, including public bodies) rather than listed
  companies; AFM publishes no Netherlands headcount, and the "~105" in trade
  press is rounded and uncitable; CMVM publishes no per-market count; Ecuador
  publishes only bond issuers; Ukraine's exchange register holds no domestic
  equity issuer. With the 6 never-reporting countries, 60 of 71 have a 2025
  value.
- Confidence varies and is recorded per row. High: Argentina (83), Costa Rica
  (9), Israel (524), Italy (187), Mexico (127), Russia (215), Sweden (363).
  Medium: Denmark (114), Finland (136), Norway (181), Slovakia (24). Low:
  France (339), Ireland (15), UK (1,199 — derived).
- Every value is traceable to its method, source year and URL, so a reviewer
  can audit or replace any single row.
- `Listed_companies` is no longer uniformly observed. Anything that describes
  it as a measured fact must say which countries are estimates.
- Enforced in `scripts/build_listed_companies_2025.py` (`_validate` asserts 0
  carry-forwards, 14 exchange lookups, 19 stale rows, and that `missing` rows
  carry no value) and repeated in `scripts/build_denominators.py`.
- Some exchange counts still differ from WDI's domestic basis: the Nordic
  figures include foreign-domiciled issuers, and WFE publishes only a combined
  "Nasdaq Nordic and Baltics" line, so a per-country domestic re-cut is not
  available. Each lookup records that caveat.
