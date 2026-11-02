# WIPO GII indicator eye-test — findings

This note summarises the indicator-level plausibility screen of the WIPO Global Innovation Index (GII) columns evaluated for possible use in the SIDE/CHIPS composite. The analysis is reproduced in `gii_eye_test.ipynb`; the underlying outputs are the CSV files in this folder.

The screen was run **before CHIPS inclusion**, on the **latest available year** for each indicator rather than the full panel. It is a screening exercise: a flag means "investigate before using", not "reject".

## Scope and method

- **Input**: `data/WIPO Global Innovation Index/gii_indicators_side2026_countries.csv` (71 countries × 41 columns).
- **20 numeric columns**: 18 indicators (13 fetched + 5 derived) plus 2 denominators (population and GDP, PPP).
- **71 countries** in the dashboard universe.
- Each indicator was assigned a plausible CHIPS home pillar, then injected as a **shadow sub-pillar** at equal weight with the existing sub-pillars in that pillar.
- Sensitivity was tested under **Absolute/Relative × min-max/z-score**.
- Tests covered:
  - coverage, latest year and staleness;
  - domain bounds, robust z-scores, Tukey fences, skew and `max/median`;
  - size artefacts against log GDP and log population;
  - country known-fact spot checks;
  - construct validity against the existing target-pillar score;
  - raw-versus-derived consistency;
  - CHIPS score and rank change from adding the indicator.

## Headline findings

1. **The raw count indicators mostly measure economy size, not innovation intensity.** Resident patents, scientific articles, GitHub pushes and OpenAlex articles have size correlations of 0.82–0.88 with log GDP. They need a denominator or a different normalisation if the intent is intensity.
2. **Min-max scaling is unusually fragile for this indicator set.** `max/median` ratios run from 34 to 2,250 for several count measures. In those cases the largest country sets the top of the 0–1 range and almost everyone else is compressed near zero.
3. **Several series contain source/provenance artefacts rather than country performance.** The clearest are GitHub in China (firewall), OpenAlex article counts (different publication universe), ICT service exports in Ireland and IP receipts in the Netherlands (transfer pricing/tax domicile), and GDP per unit of energy use in Ireland (multinational-inflated GDP).
4. **Coverage and vintage are uneven.** Market capitalisation has only 62 of 71 countries and 13 stale observations; GERD has 16 stale observations, including India's latest value from 2020. Low-carbon share and IP receipts also have material gaps.
5. **Some indicators do not align with the pillar they would sit in.** FDI and GDP per unit of energy use have near-zero or negative rank correlation with their target pillar; OpenAlex articles per GDP and low-carbon share are also weak.
6. **Even a modest shadow sub-pillar can move CHIPS ranks by dozens.** At a global shadow weight of 0.0625 (INNOVATE) or 0.0417 (HARNESS), market capitalisation and low-carbon share each move a country by 40–41 ranks under at least one setting.

## Coverage and vintage

Six indicators have less than full coverage, and three have stale observations.

| Indicator | n / 71 | Latest year (mode) | Stale (>2y) | Missing or stale countries |
|---|---:|---:|---:|---|
| Market capitalisation, % GDP | 62 | 2025 | 13 | Missing: Sweden, Denmark, Finland, Serbia, Guatemala, Dominican Republic, Ecuador, Ethiopia, Iraq. Stale: United Kingdom, France, Ireland, Netherlands, Norway, Portugal, Belgium, Italy, Costa Rica, Argentina, Slovak Republic, Ukraine, Algeria. |
| Medium/high-tech manufacturing, % MVA | 70 | 2024 | 0 | Missing: Dominican Republic |
| FDI net inflows, % GDP | 71 | 2025 | 0 | — |
| Gross R&D expenditure, % GDP | 67 | 2023 | 16 | Missing: Morocco, Ghana, Bangladesh, Dominican Republic. Stale: Singapore, India, UAE, Australia, Chile, Qatar, Malaysia, Indonesia, Colombia, Philippines, Nigeria, South Africa, Ecuador, Ethiopia, Iraq, Sri Lanka. |
| Resident patent applications | 71 | 2024 | 1 | Stale: Nigeria (2020) |
| Scientific & technical articles | 71 | 2023 | 0 | — |
| Low-carbon share of primary energy | 62 | 2025 | 0 | Missing: Costa Rica, Serbia, Nigeria, Kenya, Ghana, Guatemala, Dominican Republic, Ethiopia, Rwanda |
| GDP per unit of energy use | 71 | 2024 | 0 | — |
| GitHub git pushes 2025 | 71 | 2025 | 0 | — |
| OpenAlex articles 2024 | 71 | 2024 | 0 | — |
| OpenAlex company-authored articles 2024 | 71 | 2024 | 0 | — |
| ICT service exports, USD | 70 | 2025 | 0 | Missing: Viet Nam |
| IP receipts, USD | 67 | 2025 | 1 | Missing: Qatar, Kuwait, Viet Nam, Nigeria. Stale: Dominican Republic |
| Resident patents per bn PPP$ GDP | 71 | 2024 | 1 | Stale: Nigeria (parent year) |
| Articles per bn PPP$ GDP | 71 | 2023 | 0 | — |
| GitHub pushes per mn population | 71 | 2025 | 0 | — |
| OpenAlex articles per bn PPP$ GDP 2024 | 71 | 2024 | 0 | — |
| Company-authored article share 2024 | 71 | 2024 | 0 | — |

## Distribution and min-max domination

The indicators most exposed to min-max domination are the count measures and the two USD flow measures. `max/median` is a direct indicator of how much of the 0–1 scale is controlled by the top observation.

| Indicator | Max / median | Skew | MAD > 3.5 | Bounds violation |
|---|---:|---:|---:|---|
| Resident patent applications | 2,250.3 | 7.76 | 13 | — |
| IP receipts, USD | 557.3 | 5.39 | 22 | — |
| Resident patents per bn PPP$ GDP | 77.3 | 4.93 | 7 | — |
| ICT service exports, USD | 74.4 | 5.22 | 12 | — |
| OpenAlex company-authored articles | 74.4 | 4.43 | 16 | — |
| Scientific & technical articles | 68.8 | 6.10 | 13 | — |
| OpenAlex articles | 35.2 | 4.09 | 12 | — |
| GitHub git pushes | 34.2 | 4.69 | 9 | — |
| FDI net inflows, % GDP | 15.8 | −1.34 | 4 | — |
| Market capitalisation, % GDP | 7.7 | 1.62 | 7 | South Africa = 327.2 (> 300) |

For comparison, the least concentrated indicators are medium/high-tech manufacturing (`max/median` 2.29), articles per bn PPP$ GDP (2.31), GDP per unit of energy use (3.28) and low-carbon share (4.40).

The practical consequence is that for patents, IP receipts, ICT exports, OpenAlex articles and scientific articles, a min-max score is effectively a "distance from the top country" measure. Ordinary countries cluster near zero, and the composite becomes sensitive to the exact top value rather than to broad cross-country differences.

## Country spot-check anomalies

The curated known-fact layer flagged the following values. Some are genuine but structurally extreme; others look like provenance or source problems.

| Indicator | Country | Value | Concern |
|---|---|---:|---|
| Market capitalisation, % GDP | India | 266.9 | Jump from 136.4 in 2024; implausible one-year change, verify provenance |
| Market capitalisation, % GDP | South Africa | 327.2 | Above the 300% domain bound |
| Gross R&D expenditure, % GDP | Guatemala | 0.006% | Implausibly low |
| Gross R&D expenditure, % GDP | India | 0.646% | Latest year is 2020; stale |
| FDI net inflows, % GDP | Hungary | −28.4% | Disinvestment one-off; verify |
| GitHub git pushes 2025 | China | 8.5 mn | Firewall undercount; per-capita 6,069 vs Singapore 1.6 mn |
| GitHub pushes per mn population | China | 6,069 | Firewall plus denominator issue |
| OpenAlex articles 2024 | Indonesia | 554,200 | Above India's 305,660; OpenAlex universe inflation |
| OpenAlex articles 2024 | China | 955,206 | Publication universe differs from WIPO/Clarivate |
| ICT service exports, USD | Ireland | 358.8 bn | Multinational transfer-pricing effect; real but extreme |
| IP receipts, USD | Netherlands | 67.4 bn | Tax-domicile effect; real but extreme |
| GDP per unit of energy use | Ireland | 48.1 | GDP inflated by multinationals; efficiency overstated |
| Scientific & technical articles | India | 228,174 | Plausible, but source universe differs from OpenAlex |

## Construct validity

Construct validity here is the Spearman correlation between the candidate and the existing target-pillar score under the Absolute baseline. High values indicate alignment; very high values can also mean the candidate duplicates what the pillar already measures.

- **Strongly aligned (r ≥ 0.75):** ICT service exports (0.82), OpenAlex company-authored articles (0.85), IP receipts (0.80), resident patent applications (0.81), scientific articles (0.81), OpenAlex articles (0.77).
- **Moderately aligned (0.45–0.75):** medium/high-tech manufacturing (0.69), patents per bn GDP (0.65), GERD (0.62), market capitalisation (0.61), company-authored share (0.52).
- **Weakly aligned (0.25–0.45):** GitHub pushes per mn population (0.42), articles per bn GDP (0.35), low-carbon share (0.27).
- **Not aligned (r ≤ 0.25):** OpenAlex articles per bn GDP (0.16), FDI (−0.09), GDP per unit of energy use (−0.04).

FDI and GDP per unit of energy use are the clearest cases where the indicator appears to measure something other than the target pillar. The per-GDP OpenAlex measures are also weak, which is consistent with the normalisation shifting them away from the innovation construct.

## Raw versus derived indicators

Normalisation removes the size artefact, but it does not preserve the ranking of the raw measure. The two versions should therefore be treated as different indicators, not substitutes.

| Raw | Derived | Spearman(raw, derived) | Size r(GDP), raw | Size r(GDP), derived |
|---|---|---|---:|---:|
| Resident patent applications | Patents per bn PPP$ GDP | 0.863 | 0.82 | 0.48 |
| Scientific & technical articles | Articles per bn PPP$ GDP | 0.477 | 0.85 | −0.01 |
| GitHub git pushes | GitHub pushes per mn population | 0.349 | 0.84 | 0.03 |
| OpenAlex articles | OpenAlex articles per bn PPP$ GDP | 0.318 | 0.88 | −0.10 |
| OpenAlex articles | Company-authored article share | 0.182 | 0.88 | 0.08 |

The derived series remove the large-economy advantage (size correlations fall to between −0.10 and 0.48), but the weak rank correlations mean they are capturing a different construct. For example, the OpenAlex per-GDP measure puts Ukraine and Indonesia at the top, and the articles-per-GDP measure puts Portugal, Denmark and Finland at the top. These are not simply "the same ranking with size removed".

## CHIPS influence as a shadow sub-pillar

The table shows the worst case across Absolute/Relative × min-max/z-score. `ΔCHIPS` is the maximum absolute change in a country's CHIPS score; `Δrank` is the maximum absolute change in CHIPS rank.

| Indicator | Pillar | Shadow weight | max abs ΔCHIPS | max abs Δrank | Top mover |
|---|---|---|---:|---:|---|
| Market capitalisation, % GDP | INNOVATE | 0.0625 | 0.065 | 41 | South Africa (+0.062) |
| Low-carbon share of primary energy | SUSTAINABILITY | 0.0625 | 0.041 | 40 | Sweden (+0.039) |
| OpenAlex articles per bn PPP$ GDP | INNOVATE | 0.0625 | 0.091 | 38 | Ukraine (+0.061) |
| Company-authored article share | INNOVATE | 0.0625 | 0.086 | 37 | Greece (+0.061) |
| FDI net inflows, % GDP | INNOVATE | 0.0625 | 0.059 | 31 | Singapore (+0.059) |
| Articles per bn PPP$ GDP | INNOVATE | 0.0625 | 0.088 | 27 | Portugal (+0.062) |
| Medium/high-tech manufacturing | HARNESS | 0.0417 | 0.037 | 26 | Qatar (+0.037) |
| GDP per unit of energy use | SUSTAINABILITY | 0.0625 | 0.041 | 23 | Ireland (+0.041) |
| ICT service exports, USD | HARNESS | 0.0417 | 0.037 | 22 | Ireland (+0.037) |
| Gross R&D expenditure, % GDP | INNOVATE | 0.0625 | 0.105 | 21 | Israel (+0.060) |
| OpenAlex company-authored articles | INNOVATE | 0.0625 | 0.106 | 19 | China (+0.030) |
| OpenAlex articles | INNOVATE | 0.0625 | 0.106 | 19 | China (+0.036) |
| Resident patents per bn PPP$ GDP | INNOVATE | 0.0625 | 0.107 | 18 | Korea (+0.059) |
| Resident patent applications | INNOVATE | 0.0625 | 0.107 | 18 | United States (−0.051) |
| IP receipts, USD | INNOVATE | 0.0625 | 0.063 | 18 | China (−0.023) |
| Scientific & technical articles | INNOVATE | 0.0625 | 0.107 | 18 | China (+0.036) |
| GitHub pushes per mn population | HARNESS | 0.0417 | 0.037 | 16 | Singapore (+0.037) |
| GitHub git pushes | HARNESS | 0.0417 | 0.026 | 9 | China (−0.026) |

Two things stand out. First, the biggest rank effects are not always the biggest score effects: market capitalisation moves 41 ranks with only a 0.065 CHIPS-point change, and low-carbon share moves 40 ranks with 0.041 points. Second, adding any one of these at full sub-pillar weight is a substantial structural change in a 71-country ranking; the shadow weight was deliberately generous, so this is an upper-bound test rather than a proposed weighting.

## Indicator-level summary

Sorted by worst-case CHIPS rank change. "Flags" follows the scorecard labels (`bounds`, `coverage`, `stale`, `outliers`, `minmax-dominated`, `size-driven`).

| Indicator | Coverage | Latest yr | Stale | Max/median | Size r(GDP) | Construct r | max Δrank | Flags |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Market capitalisation, % GDP | 62 | 2025 | 13 | 7.70 | 0.41 | 0.61 | 41 | bounds; stale; outliers |
| Low-carbon share of primary energy | 62 | 2025 | 0 | 4.40 | −0.12 | 0.27 | 40 | outliers |
| OpenAlex articles per bn PPP$ GDP | 71 | 2024 | 0 | 3.92 | −0.10 | 0.16 | 38 | outliers |
| Company-authored article share | 71 | 2024 | 0 | 6.06 | 0.08 | 0.52 | 37 | outliers |
| FDI net inflows, % GDP | 71 | 2025 | 0 | 15.80 | −0.18 | −0.09 | 31 | outliers |
| Articles per bn PPP$ GDP | 71 | 2023 | 0 | 2.31 | −0.01 | 0.35 | 27 | OK |
| Medium/high-tech manufacturing | 70 | 2024 | 0 | 2.29 | 0.35 | 0.69 | 26 | OK |
| GDP per unit of energy use | 71 | 2024 | 0 | 3.28 | 0.02 | −0.04 | 23 | OK |
| ICT service exports, USD | 70 | 2025 | 0 | 74.42 | 0.48 | 0.82 | 22 | outliers; minmax-dominated |
| Gross R&D expenditure, % GDP | 67 | 2023 | 16 | 6.24 | 0.25 | 0.62 | 21 | stale; outliers |
| OpenAlex company-authored articles | 71 | 2024 | 0 | 74.42 | 0.69 | 0.85 | 19 | outliers; minmax-dominated |
| OpenAlex articles | 71 | 2024 | 0 | 35.20 | 0.88 | 0.77 | 19 | outliers; minmax-dominated; size-driven |
| Resident patents per bn PPP$ GDP | 71 | 2024 | 1 | 77.29 | 0.48 | 0.65 | 18 | stale; outliers; minmax-dominated |
| Resident patent applications | 71 | 2024 | 1 | 2,250.34 | 0.82 | 0.81 | 18 | stale; outliers; minmax-dominated; size-driven |
| IP receipts, USD | 67 | 2025 | 1 | 557.34 | 0.51 | 0.80 | 18 | stale; outliers; minmax-dominated |
| Scientific & technical articles | 71 | 2023 | 0 | 68.83 | 0.85 | 0.81 | 18 | outliers; minmax-dominated; size-driven |
| GitHub pushes per mn population | 71 | 2025 | 0 | 9.25 | 0.03 | 0.42 | 16 | OK |
| GitHub git pushes | 71 | 2025 | 0 | 34.15 | 0.84 | 0.75 | 9 | outliers; minmax-dominated; size-driven |

## Interpretation by group

**Count measures (patents, articles, GitHub, OpenAlex).** These are the clearest size-driven group. Normalising by GDP or population fixes the size artefact but changes the indicator enough that it can no longer be treated as the same measure. The source universes also differ: OpenAlex and WDI/Clarivate do not produce the same article counts, and GitHub does not observe activity inside the firewall in China.

**Min-max-sensitive ratio measures (IP receipts, ICT exports, patents per bn GDP).** Even after normalisation, these remain highly concentrated. IP receipts are dominated by the United States and by tax-domicile economies such as the Netherlands; ICT exports are dominated by Ireland's transfer-pricing-inflated services exports. These are legitimate recorded flows but not clean measures of domestic innovation capacity.

**Percentage-of-GDP or percentage-share measures (GERD, market capitalisation, FDI, low-carbon share).** The domain bounds are mostly respected, except for South Africa's market-capitalisation value. The main problems are vintage and missingness rather than scale: GERD has 16 stale observations, market capitalisation has 13 stale plus nine missing countries, and low-carbon share is missing nine countries. FDI also has a heavy negative tail and a very high kurtosis.

**Inputs with questionable construct alignment (FDI, GDP per unit of energy use).** These are close to zero or negative against the target pillar. They may still be reasonable policy variables in a different framework, but as innovation-pillar indicators they add noise rather than signal.

**Mechanically clean but still caveated (medium/high-tech manufacturing, articles per bn GDP, GitHub per mn population).** These have acceptable coverage (except one missing country for manufacturing), low `max/median`, and no strong size artefact. They are not automatically safe: manufacturing is a narrow industrial-structure measure, articles per bn GDP is weakly aligned with the innovation pillar, and GitHub per capita inherits the China firewall problem even after population normalisation.

## Follow-up questions before any use

- Verify the market-capitalisation jump for India (136.4 in 2024 to 266.9 in 2025) and the South Africa value above the domain bound.
- Decide explicitly whether the intended construct is **scale** (raw counts) or **intensity** (per-GDP/per-population/company share); the raw and derived series are not interchangeable.
- For min-max runs, test winsorisation or log transforms on the count and USD-flow indicators so that a single endpoint does not define the scale.
- Reconcile or annotate the OpenAlex and GitHub source universes rather than treating them as equivalent to WDI/Clarivate or to total national activity.
- Treat Ireland (ICT exports, GDP per energy use), the Netherlands (IP receipts) and similar tax/transfer-pricing hubs as structural outliers, not as errors to be silently dropped.
- Refresh the stale GERD and market-capitalisation observations before using either indicator in a current-year composite.

## Outputs

The detailed tables are in this folder:

- `gii_coverage.csv` — coverage, latest year, missing and stale countries
- `gii_distribution.csv` — distribution statistics, bounds, size correlations, top/bottom three
- `gii_outliers.csv` — country-level robust-z and Tukey flags
- `gii_known_fact_notes.csv` — curated country spot-check notes
- `gii_country_spotchecks.csv` — wide spot-check panel for 18 economies
- `gii_construct_validity.csv` — correlation with target pillar, Absolute and Relative
- `gii_chips_influence.csv` — shadow sub-pillar influence, all base/method runs
- `gii_chips_influence_country.csv` — country-level CHIPS and rank changes
- `gii_scorecard.csv` — one-row-per-indicator screening scorecard

No inclusion recommendation is made here. The purpose of the screen is to identify which numbers need verification, which need a different normalisation, and which are structurally unsuitable for an equal-weight composite.
