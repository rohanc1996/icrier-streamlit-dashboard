# The Need for a Data Audit in Innovation Index Rankings

*A close look at the indicators behind the WIPO Global Innovation Index shows which data problems survive its own pre-treatment — and which do not.*

Innovation rankings are influential. They inform budget speeches, investment pitches and ministry talking points. But a composite index is a chain of choices: what to measure, how to normalise it, which year to use, and how much weight to give each indicator. A plausible-looking rank can hide a great deal of expert subjectivity, measurement uncertainty and provenance artefacts.

We recently ran an indicator-level test on 18 indicators from the WIPO Global Innovation Index (GII) across 71 economies. The exercise was not a critique of the GII as a whole. It was a quality-control check on the underlying numbers before we used them ourselves: are they complete, current, comparable across countries, and aligned with what they claim to measure?

Our first pass looked at the raw indicator values. But that is not how WIPO builds the index. WIPO normalises to a 0–100 scale using **min-max**, not z-scores, and it treats outliers before doing so. So we re-ran the analysis after recreating that pre-treatment, mapping each indicator to its GII treatment where an equivalent series exists and applying WIPO's general rule to the remaining proxies. The results change the story in important ways.

## WIPO does not min-max raw counts

WIPO's methodology treats problematic hard-data series before scaling them. Indicators with high skewness and kurtosis are winsorised if they have one to five outliers, and log-transformed if they have more. Only then are they min-max normalised and aggregated.

That matters. In our raw data, resident patent applications had a maximum 2,250 times the median; scientific articles, 69 times; GitHub pushes, 34 times; and OpenAlex articles, 35 times. On a raw min-max scale, the largest country sets the top of the range and almost everyone else is compressed near zero.

After applying WIPO's pre-treatment, that compression largely disappears in our 71-economy sample. The median normalised score for resident patent applications rises from effectively zero to 0.46; for scientific articles to 0.69; for GitHub pushes to 0.81; and for OpenAlex articles to 0.74. The share of countries scoring below 0.25 falls from 93–99% to between 1% and 10%.

## But pre-treatment does not fix everything

The improvement is uneven. Several ratio and percentage indicators remain highly concentrated even after WIPO's treatment.

Resident patents per billion PPP dollars of GDP is log-transformed in the GII, yet 76% of countries still score below 0.25 on a min-max scale. Market capitalisation and low-carbon share each leave about 58% of countries below 0.25; GDP per unit of energy use, 56%; GERD, 69%; company-authored article share, 62%; and OpenAlex articles per GDP, 52%.

FDI is a particularly instructive case. Winsorising the negative outlier raises the minimum and shrinks the range, so the share of countries below 0.25 rises from 1.4% before treatment to 78.9% after. Treatment can change the shape of a distribution without making it more even.

For these indicators, min-max still turns the score into a distance-from-the-top measure. The problem is not that WIPO ignores outliers; it is that the underlying distributions remain top-heavy even after the standard treatment.

## Pre-treatment can increase influence, not reduce it

We also tested how much one indicator can move a composite when added as a full sub-pillar. The effects are large, and pre-treatment does not always make them smaller.

Before treatment, market capitalisation moved a country by up to 41 ranks and FDI by 31. After treatment, those effects fall to 38 and 20. But other indicators become more influential. IP receipts rises from an 18-rank swing to 33; OpenAlex articles from 19 to 31; GitHub pushes from 9 to 23; and scientific articles from 18 to 30.

The reason is that log transformation spreads the middle of the distribution. It removes the extreme tail, but it can also give more countries distinctive scores, so the indicator reshuffles more of the ranking. Pre-treatment is not a stability guarantee.

## Some numbers are source artefacts, not country performance

Several extreme values reflect how the information is collected rather than how innovative a country is. Pre-treatment does not address any of these.

GitHub data show China with 8.5 million pushes, compared with 139.8 million in the United States and 117.9 million in India. That is most likely a firewall effect, not a measure of Chinese coding activity. On a per-capita basis, China records about 6,000 pushes per million people, while Singapore records about 1.6 million.

OpenAlex article counts tell a similar cautionary tale. Indonesia records 554,000 articles in 2024, above India's 306,000. That does not mean Indonesia produces more research than India. OpenAlex covers a different publication universe from WDI or Clarivate, and the totals are not directly comparable.

Other extremes are genuine recorded flows but poor proxies for domestic capability. Ireland's ICT service exports are $358.8 billion, shaped heavily by multinational transfer pricing. The Netherlands records $67.4 billion in IP receipts, reflecting its role as a tax domicile. Ireland's GDP per unit of energy use is inflated by multinational accounting.

These numbers should not be silently dropped. But they should be labelled for what they are.

## Missing and stale data quietly distort comparisons

Coverage is uneven. Market capitalisation covers only 62 of the 71 economies, and 13 of those observations are more than two years old. Sweden, Denmark and Finland are missing entirely. Gross R&D expenditure covers 67 economies, but 16 observations are stale, including India's latest value from 2020. Low-carbon share covers 62 economies; IP receipts cover 67.

This matters because a ranking can end up comparing India's 2020 R&D intensity with another country's 2025 value. The rank looks precise, but the comparison is not like-for-like. Publishing the vintage of each indicator is not cosmetic; it is part of the measurement.

## What this means for India

Three findings are particularly relevant for India.

First, India's market capitalisation is recorded at 266.9% of GDP in 2025, up from 136.4% in 2024. That one-year jump is large enough to warrant a provenance check before it is used in any ranking. WIPO's winsorisation reduces its influence at the top, but it does not make the underlying value more credible.

Second, India's R&D expenditure is based on a 2020 observation. Any current innovation comparison that uses this indicator is partly comparing the present with the past.

Third, India's raw research counts are lower than China's — 63,217 resident patent applications versus 1.67 million — but the gap narrows on a per-GDP basis: 3.7 versus 40.5 patents per billion PPP dollars of GDP. That is still a substantial gap, but it is a different story from the raw totals. Which story gets told depends on the normalisation choice.

## What should index producers and users do?

The GII remains a useful starting point. The issue is not that composite indices are worthless. It is that they need to be read as structured arguments, not as direct measurements.

Five practical steps would help:

- Publish coverage, vintage and the pre-treatment applied to every indicator, not just the final score.
- Separate scale indicators from intensity indicators, and state which construct is being ranked.
- Test whether the remaining ratio indicators need further treatment or a different scaling method; WIPO's existing winsorisation and log treatment already remove most count compression, but not all ratio compression.
- Flag source artefacts and structural outliers — firewall effects, publication-universe differences, transfer-pricing hubs — instead of treating them as ordinary observations.
- Report sensitivity to indicator choice and weighting after pre-treatment, ideally as a rank range rather than a single number.

A data audit is not an attack on an index. It is quality control. The first step to better innovation policy is better measurement — and better measurement begins by asking what the numbers actually represent.

---

*The analysis screened 18 WIPO GII indicators across 71 economies using the latest available year for each. It assessed coverage, vintage, distributional outliers, size bias, source comparability, construct validity, and influence on a composite score, both before and after recreating WIPO's documented pre-treatment. WIPO's pre-treatment and normalisation rules are described in the GII 2024 and 2025 methodology appendices. The views are those of the author.*
