# The Need for a Data Audit in Innovation Index Rankings
*A close look at the indicators behind the WIPO Global Innovation Index shows how scale, source artefacts and stale data can shape a country's rank.*


Innovation rankings are influential. They inform budget speeches, investment pitches and ministry talking points. But a composite index is a chain of choices: what to measure, how to normalise it, which year to use, and how much weight to give each indicator. A plausible-looking rank can hide a great deal of expert subjectivity, measurement uncertainty and provenance artefacts.

We recently ran an indicator-level test on 18 indicators from the WIPO Global Innovation Index (GII) across 71 economies. The exercise was not a critique of the GII as a whole, but rather a quality-control check on the underlying numbers before we used them to draw conclusions ourselves: are they complete, current, comparable across countries, and aligned with what they claim to measure?

We made several concerning findings.

## Scale can masquerade as innovation

The raw count indicators are dominated by the largest economies. Resident patent applications had a maximum of 1.67 million and a median of 743 — a ratio of more than 2,000 to one. Scientific and technical articles had a maximum 69 times the median; GitHub pushes and OpenAlex article counts were 34 and 35 times the median respectively.

These indicators are also strongly correlated with log GDP: 0.82 for patent applications, 0.85 for scientific articles, 0.84 for GitHub pushes and 0.88 for OpenAlex articles. That is not necessarily a flaw; innovation activity does scale with economy size. But it becomes a problem when raw counts are placed on a min-max scale: the largest country sets the top of the range, and almost everyone else is compressed near zero.


## Normalisation changes the story

The obvious fix is to divide by GDP or population. But normalised indicators are not simply the raw ones with size removed. They rank countries differently.

The rank correlation between resident patent applications and patents per billion PPP dollars of GDP was 0.86. For scientific articles and articles per GDP it was only 0.48; for GitHub pushes and pushes per million people, 0.35; for OpenAlex articles and articles per GDP, 0.32.

Some of these differences are revealing. Articles per GDP put Portugal, Denmark and Finland at the top; OpenAlex articles per GDP put Ukraine and Indonesia at the top. Those are not the same countries that lead on raw research output. They may be measuring openness, small-economy effects or source coverage rather than innovation capacity.

The lesson is that "per GDP" is not a neutral correction. It is a different indicator, with a different economic meaning.

## Some numbers are source artefacts, not country performance

Several extreme values in the data appear to reflect how the information is collected rather than how innovative a country is.

GitHub data show China with 8.5 million pushes, compared with 139.8 million in the United States and 117.9 million in India. That is almost certainly a firewall effect, not a measure of Chinese coding activity. On a per-capita basis, China records about 6,000 pushes per million people, while Singapore records about 1.6 million.

OpenAlex article counts tell a similar cautionary tale. Indonesia records 554,000 articles in 2024, above India's 306,000. That does not mean Indonesia produces more research than India. OpenAlex covers a different publication universe from WDI or Clarivate, and the totals are not directly comparable.

Other extremes are genuine recorded flows but poor proxies for domestic capability. Ireland's ICT service exports are $358.8 billion, shaped heavily by multinational transfer pricing. The Netherlands records $67.4 billion in IP receipts, reflecting its role as a tax domicile. Ireland's GDP per unit of energy use is inflated by multinational accounting.

These numbers should not be silently dropped. But they should be labelled for what they are.

## Missing and stale data quietly distort comparisons

Coverage is uneven. Market capitalisation covers only 62 of the 71 economies, and 13 of those observations are more than two years old. Sweden, Denmark and Finland are missing entirely. Gross R&D expenditure covers 67 economies, but 16 observations are stale, including India's latest value from 2020. Low-carbon share covers 62 economies; IP receipts cover 67.

This matters because a ranking can end up comparing India's 2020 R&D intensity with another country's 2025 value. The rank looks precise, but the comparison is not like-for-like. Publishing the vintage of each indicator is not cosmetic; it is part of the measurement.

## A single indicator can swing the result

We also tested how much one indicator can change a composite score when added as a full sub-pillar. The effects were large. Market capitalisation moved a country by up to 41 ranks in at least one specification; low-carbon share by 40; OpenAlex articles per GDP by 38; company-authored article share by 37; and FDI by 31.

The weights were deliberately generous, so these are upper-bound estimates. But the broader point holds: in a 71-country ranking, a single measurement choice can move a country by dozens of places. A rank without a sensitivity test can create false confidence.

## What this means for India

Three findings are particularly relevant for India.

First, India's market capitalisation is recorded at 266.9% of GDP in 2025, up from 136.4% in 2024. That one-year jump is large enough to warrant a provenance check before it is used in any ranking.

Second, India's R&D expenditure is based on a 2020 observation. Any current innovation comparison that uses this indicator is partly comparing the present with the past.

Third, India's raw research counts are lower than China's — 63,217 resident patent applications versus 1.67 million — but the gap narrows on a per-GDP basis: 3.7 versus 40.5 patents per billion PPP dollars of GDP. That is still a substantial gap, but it is a different story from the raw totals. Which story gets told depends on the normalisation choice.

## What should index producers and users do?

The GII remains a useful starting point. The issue is not that composite indices are worthless. It is that they need to be read as structured arguments, not as direct measurements.

Five practical steps would help:

- Publish coverage and vintage for every indicator, alongside the score.
- Separate scale indicators from intensity indicators, and state which construct is being ranked.
- Use robust scaling for heavy-tailed indicators, rather than letting one country define the min-max range.
- Flag source artefacts and structural outliers — firewall effects, publication-universe differences, transfer-pricing hubs — instead of treating them as ordinary observations.
- Report sensitivity to indicator choice and weighting, ideally as a rank range rather than a single number.

A data audit is not an attack on an index. It is quality control. The first step to better innovation policy is better measurement — and better measurement begins by asking what the numbers actually represent.

---

*The analysis screened 18 WIPO GII indicators across 71 economies using the latest available year for each. It assessed coverage, vintage, distributional outliers, size bias, source comparability, construct validity, and influence on a composite score. The views are those of the author.*
