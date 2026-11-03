# WIPO GII indicator eye-test — findings

This note summarises the indicator-level plausibility screen of the WIPO Global Innovation Index (GII) columns evaluated for possible use in the SIDE/CHIPS composite. The analysis is reproduced in `gii_eye_test.ipynb`; a second pass that recreates WIPO's documented pre-treatment is in `scripts/wipo_pretreatment_analysis.py`, with outputs under `deliverables/gii-eye-test/pretreatment/`.

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
- The second pass replicates WIPO's documented pre-treatment before min-max: treating hard-data indicators with high skewness and kurtosis, winsorising series with one to five outliers, log-transforming series with more, and mapping each indicator to its GII 2025 treatment where an equivalent GII series exists. Details are in the pre-treatment section below.

## Headline findings

1. **The raw count indicators mostly measure economy size, not innovation intensity.** Resident patents, scientific articles, GitHub pushes and OpenAlex articles have size correlations of 0.82–0.88 with log GDP. They need a denominator or a different normalisation if the intent is intensity.
2. **WIPO's pre-treatment removes most of the raw-count problem.** WIPO applies min-max, but only after treating outliers. Once we replicate that treatment, the median normalised score for the count measures rises from near zero to 0.46–0.84, and the share of countries scoring below 0.25 falls from 93–99% to 1–10%. The raw-count critique is not a critique of the final GII.
3. **The pre-treatment does not fix the ratio and percentage indicators.** After treatment, 76% of countries still score below 0.25 on patents per bn PPP$ GDP, 58% on market capitalisation, 58% on low-carbon share, 56% on GDP per unit of energy use, 69% on GERD, 62% on company-authored article share and 52% on OpenAlex articles per GDP. These remain exposed to min-max domination.
4. **Several series contain source/provenance artefacts rather than country performance.** The clearest are GitHub in China (firewall), OpenAlex article counts (different publication universe), ICT service exports in Ireland and IP receipts in the Netherlands (transfer pricing/tax domicile), and GDP per unit of energy use in Ireland (multinational-inflated GDP). Pre-treatment does not address any of these.
5. **Coverage and vintage are uneven.** Market capitalisation has only 62 of 71 countries and 13 stale observations; GERD has 16 stale observations, including India's latest value from 2020. Low-carbon share and IP receipts also have material gaps.
6. **Some indicators do not align with the pillar they would sit in.** FDI and GDP per unit of energy use have near-zero or negative rank correlation with their target pillar; OpenAlex articles per GDP and low-carbon share are also weak.
7. **Pre-treatment can increase an indicator's influence, not reduce it.** Log-transforming a count spreads the middle of the distribution, so adding it to a composite can reshuffle more ranks. IP receipts moves from an 18-rank swing before treatment to 33 after; OpenAlex articles from 19 to 31; GitHub pushes from 9 to 23; scientific articles from 18 to 30. Market capitalisation and FDI move less.

## Coverage and vintage

Six indicators have less than full coverage, and five have stale observations.

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

## Raw distribution and min-max domination

This section describes the indicators **before** WIPO-style pre-treatment. The raw `max/median` ratio shows how much of a 0–1 min-max scale is controlled by the top observation.

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

The practical consequence for the **raw** series is that patents, IP receipts, ICT exports, OpenAlex articles and scientific articles produce a min-max score that is effectively a "distance from the top country" measure. Ordinary countries cluster near zero, and the composite becomes sensitive to the exact top value rather than to broad cross-country differences.

## Recreating WIPO's pre-treatment

WIPO does not min-max raw values. Its 2024 and 2025 methodology appendices describe the following sequence:

- Indicators with absolute skewness above 2.25 and kurtosis above 3.5 are treated. Indicators with one to five outliers are winsorised; indicators with more than five are log-transformed. The JRC audit also recommends inspecting indicators with kurtosis above 10 when skewness is below 2.25.
- The log formula scales the series to `[1, max]` before taking natural logs, so the minimum maps to zero: `ln(((max - 1)(x - min) / (max - min)) + 1)`.
- After pre-treatment, all indicators are min-max normalised to `[0, 100]`, not z-scored. Aggregation is by weighted arithmetic averages.

We mapped each indicator to its GII 2025 treatment where an equivalent series exists: 4.2.1 market capitalisation (winsorise top two), 5.3.4 FDI (winsorise bottom one), 6.1.1 patents per bn PPP$ GDP (log), 6.1.4 articles per bn PPP$ GDP (no treatment), 7.3.2 GitHub pushes per mn population (winsorise top one), and 6.2.4, 2.3.2, 3.3.2 and 3.3.1 (no treatment). For the raw counts and OpenAlex/ICT/IP proxies that do not map directly to a GII indicator, we applied WIPO's generic selection and treatment rule to the series as pulled.

The effect is large for the count measures and limited for the ratio measures:

| Indicator | Treatment applied | Median normalised, raw | Median normalised, after | Share < 0.25, raw | Share < 0.25, after |
|---|---|---:|---:|---:|---:|
| Resident patent applications | log | 0.000 | 0.461 | 0.986 | 0.099 |
| Scientific & technical articles | log | 0.014 | 0.692 | 0.972 | 0.028 |
| GitHub git pushes | log | 0.028 | 0.809 | 0.958 | 0.014 |
| OpenAlex articles | log | 0.028 | 0.740 | 0.944 | 0.014 |
| OpenAlex company-authored articles | log | 0.013 | 0.596 | 0.930 | 0.028 |
| ICT service exports, USD | log | 0.013 | 0.838 | 0.957 | 0.014 |
| IP receipts, USD | log | 0.002 | 0.757 | 0.925 | 0.015 |
| Resident patents per bn PPP$ GDP | log (GII 6.1.1) | 0.013 | 0.136 | 0.958 | 0.761 |
| Market capitalisation, % GDP | winsor top 2 (GII 4.2.1) | 0.129 | 0.176 | 0.694 | 0.581 |
| Low-carbon share of primary energy | none (GII 3.3.2) | 0.227 | 0.227 | 0.581 | 0.581 |
| GDP per unit of energy use | none (GII 3.3.1) | 0.229 | 0.229 | 0.563 | 0.563 |
| Gross R&D expenditure, % GDP | none (GII 2.3.2) | 0.160 | 0.160 | 0.687 | 0.687 |
| GitHub pushes per mn population | winsor top 1 (GII 7.3.2) | 0.105 | 0.239 | 0.831 | 0.507 |
| OpenAlex articles per bn PPP$ GDP | none | 0.243 | 0.243 | 0.521 | 0.521 |
| Company-authored article share | none | 0.154 | 0.154 | 0.620 | 0.620 |
| FDI net inflows, % GDP | winsor bottom 1 (GII 5.3.4) | 0.549 | 0.186 | 0.014 | 0.789 |
| Medium/high-tech manufacturing | none (GII 6.2.4) | 0.416 | 0.416 | 0.229 | 0.229 |
| Articles per bn PPP$ GDP | none (GII 6.1.4) | 0.426 | 0.426 | 0.268 | 0.268 |

Two results are especially important. First, **log-transforming the count measures works**: for resident patent applications, scientific articles, GitHub pushes, OpenAlex articles, company-authored articles, ICT exports and IP receipts, the share of countries below 0.25 falls to between 1% and 10%. The raw-count compression problem is largely a problem of using raw counts, not of the GII's treatment of them.

Second, **the ratio and percentage indicators remain concentrated**. Patents per bn GDP is log-transformed in the GII but 76% of countries still score below 0.25. Market capitalisation, low-carbon share, GDP per unit of energy use, GERD, company-authored share and OpenAlex articles per GDP are similarly top-heavy. FDI is a special case: winsorising the negative outlier raises the minimum and shrinks the range, so the share below 0.25 rises from 1.4% to 78.9%. Treatment can change the shape of a distribution without making it more even.

## Country spot-check anomalies

The curated known-fact layer flagged the following values. Some are genuine but structurally extreme; others look like provenance or source problems. Pre-treatment does not resolve these.

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

Normalisation removes the size artefact, but it does not preserve the ranking of the raw measure. The two versions should therefore be treated as different indicators, not substitutes. Log transformation preserves ranks; winsorisation can change them through ties.

| Raw | Derived | Spearman(raw, derived) | Size r(GDP), raw | Size r(GDP), derived |
|---|---|---|---:|---:|
| Resident patent applications | Patents per bn PPP$ GDP | 0.863 | 0.82 | 0.48 |
| Scientific & technical articles | Articles per bn PPP$ GDP | 0.477 | 0.85 | −0.01 |
| GitHub git pushes | GitHub pushes per mn population | 0.349 | 0.84 | 0.03 |
| OpenAlex articles | OpenAlex articles per bn PPP$ GDP | 0.318 | 0.88 | −0.10 |
| OpenAlex articles | Company-authored article share | 0.182 | 0.88 | 0.08 |

The derived series remove the large-economy advantage (size correlations fall to between −0.10 and 0.48), but the weak rank correlations mean they are capturing a different construct. For example, the OpenAlex per-GDP measure puts Ukraine and Indonesia at the top, and the articles-per-GDP measure puts Portugal, Denmark and Finland at the top. These are not simply "the same ranking with size removed".

## CHIPS influence after pre-treatment

The table shows the worst case across Absolute/Relative × min-max/z-score, using the pre-treated values. `ΔCHIPS` is the maximum absolute change in a country's CHIPS score; `Δrank` is the maximum absolute change in CHIPS rank. The "before" column is the corresponding maximum rank change with raw values.

| Indicator | Pillar | Shadow weight | max abs ΔCHIPS | max abs Δrank (after) | max abs Δrank (before) | Top mover |
|---|---|---|---:|---:|---:|---|
| Low-carbon share of primary energy | SUSTAINABILITY | 0.0625 | 0.041 | 40 | 40 | Sweden (+0.039) |
| Market capitalisation, % GDP | INNOVATE | 0.0625 | 0.062 | 38 | 41 | South Africa (+0.062) |
| OpenAlex articles per bn PPP$ GDP | INNOVATE | 0.0625 | 0.091 | 38 | 38 | Ukraine (+0.061) |
| Company-authored article share | INNOVATE | 0.0625 | 0.086 | 37 | 37 | Greece (+0.061) |
| IP receipts, USD | INNOVATE | 0.0625 | 0.057 | 33 | 18 | Netherlands (+0.057) |
| OpenAlex articles | INNOVATE | 0.0625 | 0.063 | 31 | 19 | Uzbekistan (+0.061) |
| GitHub pushes per mn population | HARNESS | 0.0417 | 0.038 | 31 | 16 | Switzerland (+0.038) |
| Scientific & technical articles | INNOVATE | 0.0625 | 0.063 | 30 | 18 | Uzbekistan (+0.050) |
| OpenAlex company-authored articles | INNOVATE | 0.0625 | 0.063 | 29 | 19 | Japan (+0.051) |
| Articles per bn PPP$ GDP | INNOVATE | 0.0625 | 0.088 | 27 | 27 | Portugal (+0.062) |
| Medium/high-tech manufacturing | HARNESS | 0.0417 | 0.037 | 26 | 26 | Qatar (+0.037) |
| ICT service exports, USD | HARNESS | 0.0417 | 0.042 | 25 | 22 | Kuwait (+0.042) |
| GDP per unit of energy use | SUSTAINABILITY | 0.0625 | 0.041 | 23 | 23 | Ireland (+0.041) |
| GitHub git pushes | HARNESS | 0.0417 | 0.039 | 23 | 9 | Ukraine (+0.039) |
| Resident patent applications | INNOVATE | 0.0625 | 0.079 | 22 | 18 | Korea (+0.050) |
| Gross R&D expenditure, % GDP | INNOVATE | 0.0625 | 0.105 | 21 | 21 | Israel (+0.060) |
| Resident patents per bn PPP$ GDP | INNOVATE | 0.0625 | 0.104 | 20 | 18 | Korea (+0.059) |
| FDI net inflows, % GDP | INNOVATE | 0.0625 | 0.089 | 20 | 31 | Singapore (+0.059) |

The main lesson is that pre-treatment is not a stability guarantee. It reduces the rank effect for market capitalisation (41 to 38) and FDI (31 to 20), but increases it for IP receipts (18 to 33), OpenAlex articles (19 to 31), GitHub pushes (9 to 23) and scientific articles (18 to 30). Log-transforming a series spreads the middle, which can make the indicator more consequential even as it removes the extreme tail.

## Indicator-level summary

Sorted by worst-case CHIPS rank change after pre-treatment. `Post median` and `share < 0.25` are min-max scores computed on the pre-treated series.

| Indicator | Coverage | Latest yr | Stale | Treatment | Post median | Share < 0.25 | Size r(GDP) | Construct r | max Δrank |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| Low-carbon share of primary energy | 62 | 2025 | 0 | none | 0.227 | 0.581 | −0.12 | 0.27 | 40 |
| Market capitalisation, % GDP | 62 | 2025 | 13 | winsor top 2 | 0.176 | 0.581 | 0.41 | 0.61 | 38 |
| OpenAlex articles per bn PPP$ GDP | 71 | 2024 | 0 | none | 0.243 | 0.521 | −0.10 | 0.16 | 38 |
| Company-authored article share | 71 | 2024 | 0 | none | 0.154 | 0.620 | 0.08 | 0.52 | 37 |
| IP receipts, USD | 67 | 2025 | 1 | log | 0.757 | 0.015 | 0.51 | 0.80 | 33 |
| OpenAlex articles | 71 | 2024 | 0 | log | 0.740 | 0.014 | 0.88 | 0.77 | 31 |
| GitHub pushes per mn population | 71 | 2025 | 0 | winsor top 1 | 0.239 | 0.507 | 0.03 | 0.42 | 31 |
| Scientific & technical articles | 71 | 2023 | 0 | log | 0.692 | 0.028 | 0.85 | 0.81 | 30 |
| OpenAlex company-authored articles | 71 | 2024 | 0 | log | 0.596 | 0.028 | 0.69 | 0.85 | 29 |
| Articles per bn PPP$ GDP | 71 | 2023 | 0 | none | 0.426 | 0.268 | −0.01 | 0.35 | 27 |
| Medium/high-tech manufacturing | 70 | 2024 | 0 | none | 0.416 | 0.229 | 0.35 | 0.69 | 26 |
| ICT service exports, USD | 70 | 2025 | 0 | log | 0.838 | 0.014 | 0.48 | 0.82 | 25 |
| GDP per unit of energy use | 71 | 2024 | 0 | none | 0.229 | 0.563 | 0.02 | −0.04 | 23 |
| GitHub git pushes | 71 | 2025 | 0 | log | 0.809 | 0.014 | 0.84 | 0.75 | 23 |
| Resident patent applications | 71 | 2024 | 1 | log | 0.461 | 0.099 | 0.82 | 0.81 | 22 |
| Gross R&D expenditure, % GDP | 67 | 2023 | 16 | none | 0.160 | 0.687 | 0.25 | 0.62 | 21 |
| Resident patents per bn PPP$ GDP | 71 | 2024 | 1 | log | 0.136 | 0.761 | 0.48 | 0.65 | 20 |
| FDI net inflows, % GDP | 71 | 2025 | 0 | winsor bottom 1 | 0.186 | 0.789 | −0.18 | −0.09 | 20 |

## Interpretation by group

**Count measures (patents, articles, GitHub, OpenAlex).** These are the clearest size-driven group in raw form. WIPO pre-treatment, especially log transformation, largely fixes the min-max compression: the share of countries below 0.25 falls to 1–10% for the raw counts. But the raw and scaled versions remain different indicators, and the source universes differ: OpenAlex and WDI/Clarivate do not produce the same article counts, and GitHub does not observe activity inside the firewall in China. Pre-treatment also increased the shadow influence of several count measures because it spread the middle of the distribution.

**Ratio measures that remain concentrated (patents per bn GDP, market capitalisation, low-carbon share, GDP per energy, GERD, company-authored share).** These are the post-treatment min-max problem. Patents per bn GDP is log-transformed but 76% of countries still score below 0.25. Market capitalisation and low-carbon share each leave roughly 58% below 0.25. For these indicators, min-max still turns the score into a distance-from-the-top measure.

**Min-max-sensitive flow measures (IP receipts, ICT exports).** In our data these are USD flows with different denominators from the GII's %-of-trade series, so they are proxies rather than exact GII indicators. They are dominated by the United States and by tax-domicile or transfer-pricing economies such as the Netherlands and Ireland. Log transformation removes the compression but not the source artefact, and the rank influence rises after treatment for IP receipts.

**Percentage-of-GDP or percentage-share measures (GERD, market capitalisation, FDI, low-carbon share).** The domain bounds are mostly respected, except for South Africa's market-capitalisation value. The main problems are vintage and missingness rather than scale: GERD has 16 stale observations, market capitalisation has 13 stale plus nine missing countries, and low-carbon share is missing nine countries. FDI's winsorised distribution is still highly concentrated and has a heavy positive tail after treatment.

**Inputs with questionable construct alignment (FDI, GDP per unit of energy use).** These are close to zero or negative against the target pillar. They may still be reasonable policy variables in a different framework, but as innovation-pillar indicators they add noise rather than signal.

**Mechanically clean but still caveated (medium/high-tech manufacturing, articles per bn GDP, GitHub per mn population).** These have acceptable coverage (except one missing country for manufacturing), low raw `max/median`, and no strong size artefact. They are not automatically safe: manufacturing is a narrow industrial-structure measure, articles per bn GDP is weakly aligned with the innovation pillar, and GitHub per capita inherits the China firewall problem even after population normalisation.

## Follow-up questions before any use

- Verify the market-capitalisation jump for India (136.4 in 2024 to 266.9 in 2025) and the South Africa value above the domain bound.
- Decide explicitly whether the intended construct is **scale** (raw counts) or **intensity** (per-GDP/per-population/company share); the raw and derived series are not interchangeable.
- For min-max runs, test whether the remaining ratio indicators need further treatment or a different scaling method; WIPO's existing winsorisation/log treatment already removes most count compression but not the ratio compression.
- Reconcile or annotate the OpenAlex and GitHub source universes rather than treating them as equivalent to WDI/Clarivate or to total national activity.
- Treat Ireland (ICT exports, GDP per energy use), the Netherlands (IP receipts) and similar tax/transfer-pricing hubs as structural outliers, not as errors to be silently dropped.
- Refresh the stale GERD and market-capitalisation observations before using either indicator in a current-year composite.

## Outputs

The detailed tables are in this folder:

- `gii_coverage.csv` — coverage, latest year, missing and stale countries
- `gii_distribution.csv` — raw distribution statistics, bounds, size correlations, top/bottom three
- `gii_outliers.csv` — country-level robust-z and Tukey flags
- `gii_known_fact_notes.csv` — curated country spot-check notes
- `gii_country_spotchecks.csv` — wide spot-check panel for 18 economies
- `gii_construct_validity.csv` — correlation with target pillar, Absolute and Relative
- `gii_chips_influence.csv` — shadow sub-pillar influence before pre-treatment
- `gii_chips_influence_country.csv` — country-level CHIPS and rank changes before pre-treatment
- `gii_scorecard.csv` — one-row-per-indicator screening scorecard before pre-treatment
- `pretreatment/wipo_pretreatment_map.csv` — treatment applied to each indicator
- `pretreatment/wipo_pretreatment_distribution.csv` — post-treatment distribution statistics
- `pretreatment/wipo_pretreatment_construct_validity.csv` — construct validity after treatment
- `pretreatment/wipo_pretreatment_raw_vs_derived.csv` — raw-versus-derived after treatment
- `pretreatment/wipo_pretreatment_chips_influence.csv` — shadow sub-pillar influence after treatment
- `pretreatment/wipo_pretreatment_scorecard.csv` — combined pre/post scorecard

No inclusion recommendation is made here. The purpose of the screen is to identify which numbers need verification, which need a different normalisation, and which are structurally unsuitable for an equal-weight composite.
