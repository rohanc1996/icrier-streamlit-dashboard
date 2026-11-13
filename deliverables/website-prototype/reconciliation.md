# Export reconciliation — web JSON vs CHIPS engine

Export: `data/derived/web/2026/chips.json` · edition 2026 Absolute · methods `full_minmax` (engine `full`) and `z` (engine `z`).

For each country and method below, *Exported* is the value in the JSON
payload and *Engine* is recomputed on the spot from the canonical loader
and `SIDE_dashboard/core/chips.py` (`chips_table`, `aggregate_country`,
`tree_to_frame`).

**`delta = exported - engine`, and every delta must be exactly 0.** These
are `float` subtractions, not comparisons at a tolerance: a 1e-16 drift
would show up here.

Ranks are checked *within* each method. Overall and pillar ranks can
legitimately differ between the two scalings (the composite is a weighted
sum of differently shaped transforms); that is measured in
`method-comparison.md` and is not a reconciliation failure.

## Method `full_minmax` (engine `full`)

Label: Full-range min-max.

### India (`IND`)

#### Headline and pillars

| Measure | Exported | Engine | delta |
| --- | --- | --- | --- |
| Overall CHIPS score | `0.40409999999999996` | `0.40409999999999996` | `0.0` |
| Pillar CONNECT | `0.5557708333333333` | `0.5557708333333333` | `0.0` |
| Pillar HARNESS | `0.4360333333333334` | `0.4360333333333334` | `0.0` |
| Pillar INNOVATE | `0.20799206349206348` | `0.20799206349206348` | `0.0` |
| Pillar PROTECT | `0.5116666666666667` | `0.5116666666666667` | `0.0` |
| Pillar SUSTAINABILITY | `0.32133333333333336` | `0.32133333333333336` | `0.0` |
| Sub-pillar CONNECT · Affordability score | `0.7935` | `0.7935` | `0.0` |
| Sub-pillar CONNECT · Quality score | `0.1515` | `0.1515` | `0.0` |
| Sub-pillar CONNECT · Access score | `0.72775` | `0.72775` | `0.0` |
| Sub-pillar CONNECT · AI score | `0.5503333333333333` | `0.5503333333333333` | `0.0` |
| Sub-pillar HARNESS · Apps and platform score | `0.42816666666666675` | `0.42816666666666675` | `0.0` |
| Sub-pillar HARNESS · Data Intensity score | `0.336` | `0.336` | `0.0` |
| Sub-pillar HARNESS · Fintech score | `0.255` | `0.255` | `0.0` |
| Sub-pillar HARNESS · Real Economy score | `0.7010000000000001` | `0.7010000000000001` | `0.0` |
| Sub-pillar HARNESS · AI score | `0.45999999999999996` | `0.45999999999999996` | `0.0` |
| Sub-pillar INNOVATE · Investments and Startups score | `0.18733333333333335` | `0.18733333333333335` | `0.0` |
| Sub-pillar INNOVATE · Other Emerging Technology score | `0.28314285714285714` | `0.28314285714285714` | `0.0` |
| Sub-pillar INNOVATE · AI score | `0.1535` | `0.1535` | `0.0` |
| Sub-pillar PROTECT · Preparedness score | `0.07300000000000001` | `0.07300000000000001` | `0.0` |
| Sub-pillar PROTECT · Risk of Attack score | `0.9036666666666668` | `0.9036666666666668` | `0.0` |
| Sub-pillar PROTECT · AI score | `0.5583333333333335` | `0.5583333333333335` | `0.0` |
| Sub-pillar SUSTAINABILITY · Sustainability score | `0.32133333333333336` | `0.32133333333333336` | `0.0` |
| Overall rank | `3.0` | `3.0` | `0.0` |
| Pillar rank CONNECT | `2.0` | `2.0` | `0.0` |
| Pillar rank HARNESS | `3.0` | `3.0` | `0.0` |
| Pillar rank INNOVATE | `3.0` | `3.0` | `0.0` |
| Pillar rank PROTECT | `12.0` | `12.0` | `0.0` |
| Pillar rank SUSTAINABILITY | `66.0` | `66.0` | `0.0` |
| Sub-pillar rank CONNECT · Affordability | `21.0` | `21.0` | `0.0` |
| Sub-pillar rank CONNECT · Quality | `50.0` | `50.0` | `0.0` |
| Sub-pillar rank CONNECT · Access | `2.0` | `2.0` | `0.0` |
| Sub-pillar rank CONNECT · AI | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank HARNESS · Apps and platform | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank HARNESS · Data Intensity | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank HARNESS · Fintech | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank HARNESS · Real Economy | `2.0` | `2.0` | `0.0` |
| Sub-pillar rank HARNESS · AI | `2.0` | `2.0` | `0.0` |
| Sub-pillar rank INNOVATE · Investments and Startups | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank INNOVATE · Other Emerging Technology | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank INNOVATE · AI | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank PROTECT · Preparedness | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank PROTECT · Risk of Attack | `63.0` | `63.0` | `0.0` |
| Sub-pillar rank PROTECT · AI | `14.0` | `14.0` | `0.0` |
| Sub-pillar rank SUSTAINABILITY · Sustainability | `66.0` | `66.0` | `0.0` |

#### Sample indicators

| Indicator | Raw (exported) | Raw (engine) | delta raw | Score (exported) | Score (engine) | delta score |
| --- | --- | --- | --- | --- | --- | --- |
| Number of internet users | `803000000.0` | `803000000.0` | `0.0` | `0.636` | `0.636` | `0.0` |
| Median Mobile Download Speeds (Mbps) | `132.0` | `132.0` | `0.0` | `0.18` | `0.18` | `0.0` |
| E-commerce users | `392.7` | `392.7` | `0.0` | `0.37200000000000005` | `0.37200000000000005` | `0.0` |

### Brazil (`BRA`)

#### Headline and pillars

| Measure | Exported | Engine | delta |
| --- | --- | --- | --- |
| Overall CHIPS score | `0.2546` | `0.2546` | `0.0` |
| Pillar CONNECT | `0.419125` | `0.419125` | `0.0` |
| Pillar HARNESS | `0.14471666666666666` | `0.14471666666666666` | `0.0` |
| Pillar INNOVATE | `0.05273015873015873` | `0.05273015873015873` | `0.0` |
| Pillar PROTECT | `0.4458333333333334` | `0.4458333333333334` | `0.0` |
| Pillar SUSTAINABILITY | `0.3578333333333334` | `0.3578333333333334` | `0.0` |
| Sub-pillar CONNECT · Affordability score | `0.8415` | `0.8415` | `0.0` |
| Sub-pillar CONNECT · Quality score | `0.4465` | `0.4465` | `0.0` |
| Sub-pillar CONNECT · Access score | `0.1295` | `0.1295` | `0.0` |
| Sub-pillar CONNECT · AI score | `0.25900000000000006` | `0.25900000000000006` | `0.0` |
| Sub-pillar HARNESS · Apps and platform score | `0.11883333333333335` | `0.11883333333333335` | `0.0` |
| Sub-pillar HARNESS · Data Intensity score | `0.042499999999999996` | `0.042499999999999996` | `0.0` |
| Sub-pillar HARNESS · Fintech score | `0.0905` | `0.0905` | `0.0` |
| Sub-pillar HARNESS · Real Economy score | `0.151` | `0.151` | `0.0` |
| Sub-pillar HARNESS · AI score | `0.32075` | `0.32075` | `0.0` |
| Sub-pillar INNOVATE · Investments and Startups score | `0.01966666666666667` | `0.01966666666666667` | `0.0` |
| Sub-pillar INNOVATE · Other Emerging Technology score | `0.10685714285714286` | `0.10685714285714286` | `0.0` |
| Sub-pillar INNOVATE · AI score | `0.03166666666666667` | `0.03166666666666667` | `0.0` |
| Sub-pillar PROTECT · Preparedness score | `0.0235` | `0.0235` | `0.0` |
| Sub-pillar PROTECT · Risk of Attack score | `0.8340000000000001` | `0.8340000000000001` | `0.0` |
| Sub-pillar PROTECT · AI score | `0.4800000000000001` | `0.4800000000000001` | `0.0` |
| Sub-pillar SUSTAINABILITY · Sustainability score | `0.3578333333333334` | `0.3578333333333334` | `0.0` |
| Overall rank | `7.0` | `7.0` | `0.0` |
| Pillar rank CONNECT | `6.0` | `6.0` | `0.0` |
| Pillar rank HARNESS | `8.0` | `8.0` | `0.0` |
| Pillar rank INNOVATE | `13.0` | `13.0` | `0.0` |
| Pillar rank PROTECT | `47.0` | `47.0` | `0.0` |
| Pillar rank SUSTAINABILITY | `32.0` | `32.0` | `0.0` |
| Sub-pillar rank CONNECT · Affordability | `8.0` | `8.0` | `0.0` |
| Sub-pillar rank CONNECT · Quality | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank CONNECT · Access | `5.0` | `5.0` | `0.0` |
| Sub-pillar rank CONNECT · AI | `12.0` | `12.0` | `0.0` |
| Sub-pillar rank HARNESS · Apps and platform | `5.0` | `5.0` | `0.0` |
| Sub-pillar rank HARNESS · Data Intensity | `14.0` | `14.0` | `0.0` |
| Sub-pillar rank HARNESS · Fintech | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank HARNESS · Real Economy | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank HARNESS · AI | `14.0` | `14.0` | `0.0` |
| Sub-pillar rank INNOVATE · Investments and Startups | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank INNOVATE · Other Emerging Technology | `10.0` | `10.0` | `0.0` |
| Sub-pillar rank INNOVATE · AI | `33.0` | `33.0` | `0.0` |
| Sub-pillar rank PROTECT · Preparedness | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank PROTECT · Risk of Attack | `68.0` | `68.0` | `0.0` |
| Sub-pillar rank PROTECT · AI | `18.0` | `18.0` | `0.0` |
| Sub-pillar rank SUSTAINABILITY · Sustainability | `32.0` | `32.0` | `0.0` |

#### Sample indicators

| Indicator | Raw (exported) | Raw (engine) | delta raw | Score (exported) | Score (engine) | delta score |
| --- | --- | --- | --- | --- | --- | --- |
| Number of internet users | `182000000.0` | `182000000.0` | `0.0` | `0.142` | `0.142` | `0.0` |
| Median Mobile Download Speeds (Mbps) | `260.0` | `260.0` | `0.0` | `0.36700000000000005` | `0.36700000000000005` | `0.0` |
| E-commerce users | `166.1` | `166.1` | `0.0` | `0.156` | `0.156` | `0.0` |

### Costa Rica (`CRI`)

#### Headline and pillars

| Measure | Exported | Engine | delta |
| --- | --- | --- | --- |
| Overall CHIPS score | `0.1892` | `0.1892` | `0.0` |
| Pillar CONNECT | `0.2523125` | `0.2523125` | `0.0` |
| Pillar HARNESS | `0.0032500000000000003` | `0.0032500000000000003` | `0.0` |
| Pillar INNOVATE | `0.0019500000000000001` | `0.0019500000000000001` | `0.0` |
| Pillar PROTECT | `0.4995833333333334` | `0.4995833333333334` | `0.0` |
| Pillar SUSTAINABILITY | `0.49874999999999997` | `0.49874999999999997` | `0.0` |
| Sub-pillar CONNECT · Affordability score | `0.75` | `0.75` | `0.0` |
| Sub-pillar CONNECT · Quality score | `0.22549999999999998` | `0.22549999999999998` | `0.0` |
| Sub-pillar CONNECT · Access score | `0.00125` | `0.00125` | `0.0` |
| Sub-pillar CONNECT · AI score | `0.0325` | `0.0325` | `0.0` |
| Sub-pillar HARNESS · Apps and platform score | `0.0015` | `0.0015` | `0.0` |
| Sub-pillar HARNESS · Data Intensity score | `0.002` | `0.002` | `0.0` |
| Sub-pillar HARNESS · Fintech score | `0.0005` | `0.0005` | `0.0` |
| Sub-pillar HARNESS · Real Economy score | `0.009000000000000001` | `0.009000000000000001` | `0.0` |
| Sub-pillar HARNESS · AI score | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar INNOVATE · Investments and Startups score | `0.0005` | `0.0005` | `0.0` |
| Sub-pillar INNOVATE · Other Emerging Technology score | `0.0034000000000000002` | `0.0034000000000000002` | `0.0` |
| Sub-pillar INNOVATE · AI score | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar PROTECT · Preparedness score | `0.0005` | `0.0005` | `0.0` |
| Sub-pillar PROTECT · Risk of Attack score | `0.9986666666666668` | `0.9986666666666668` | `0.0` |
| Sub-pillar PROTECT · AI score | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar SUSTAINABILITY · Sustainability score | `0.49874999999999997` | `0.49874999999999997` | `0.0` |
| Overall rank | `41.0` | `41.0` | `0.0` |
| Pillar rank CONNECT | `48.0` | `48.0` | `0.0` |
| Pillar rank HARNESS | `69.0` | `69.0` | `0.0` |
| Pillar rank INNOVATE | `68.0` | `68.0` | `0.0` |
| Pillar rank PROTECT | `17.0` | `17.0` | `0.0` |
| Pillar rank SUSTAINABILITY | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank CONNECT · Affordability | `30.0` | `30.0` | `0.0` |
| Sub-pillar rank CONNECT · Quality | `39.0` | `39.0` | `0.0` |
| Sub-pillar rank CONNECT · Access | `69.0` | `69.0` | `0.0` |
| Sub-pillar rank CONNECT · AI | `64.0` | `64.0` | `0.0` |
| Sub-pillar rank HARNESS · Apps and platform | `66.0` | `66.0` | `0.0` |
| Sub-pillar rank HARNESS · Data Intensity | `64.0` | `64.0` | `0.0` |
| Sub-pillar rank HARNESS · Fintech | `64.0` | `64.0` | `0.0` |
| Sub-pillar rank HARNESS · Real Economy | `57.0` | `57.0` | `0.0` |
| Sub-pillar rank HARNESS · AI | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar rank INNOVATE · Investments and Startups | `62.0` | `62.0` | `0.0` |
| Sub-pillar rank INNOVATE · Other Emerging Technology | `67.0` | `67.0` | `0.0` |
| Sub-pillar rank INNOVATE · AI | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar rank PROTECT · Preparedness | `55.0` | `55.0` | `0.0` |
| Sub-pillar rank PROTECT · Risk of Attack | `7.0` | `7.0` | `0.0` |
| Sub-pillar rank PROTECT · AI | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar rank SUSTAINABILITY · Sustainability | `3.0` | `3.0` | `0.0` |

#### Sample indicators

| Indicator | Raw (exported) | Raw (engine) | delta raw | Score (exported) | Score (engine) | delta score |
| --- | --- | --- | --- | --- | --- | --- |
| Number of internet users | `4477274.0` | `4477274.0` | `0.0` | `0.001` | `0.001` | `0.0` |
| Median Mobile Download Speeds (Mbps) | `71.0` | `71.0` | `0.0` | `0.091` | `0.091` | `0.0` |
| E-commerce users | `1.8` | `1.8` | `0.0` | `0.0` | `0.0` | `0.0` |

## Method `z` (engine `z`)

Label: Z-score (standardized).

### India (`IND`)

#### Headline and pillars

| Measure | Exported | Engine | delta |
| --- | --- | --- | --- |
| Overall CHIPS score | `0.6603` | `0.6603` | `0.0` |
| Pillar CONNECT | `0.6816458333333333` | `0.6816458333333333` | `0.0` |
| Pillar HARNESS | `0.8033166666666667` | `0.8033166666666667` | `0.0` |
| Pillar INNOVATE | `0.6354761904761904` | `0.6354761904761904` | `0.0` |
| Pillar PROTECT | `0.5575000000000001` | `0.5575000000000001` | `0.0` |
| Pillar SUSTAINABILITY | `0.4843333333333334` | `0.4843333333333334` | `0.0` |
| Sub-pillar CONNECT · Affordability score | `0.62125` | `0.62125` | `0.0` |
| Sub-pillar CONNECT · Quality score | `0.393` | `0.393` | `0.0` |
| Sub-pillar CONNECT · Access score | `0.987` | `0.987` | `0.0` |
| Sub-pillar CONNECT · AI score | `0.7253333333333334` | `0.7253333333333334` | `0.0` |
| Sub-pillar HARNESS · Apps and platform score | `0.8713333333333334` | `0.8713333333333334` | `0.0` |
| Sub-pillar HARNESS · Data Intensity score | `0.754` | `0.754` | `0.0` |
| Sub-pillar HARNESS · Fintech score | `0.823` | `0.823` | `0.0` |
| Sub-pillar HARNESS · Real Economy score | `0.929` | `0.929` | `0.0` |
| Sub-pillar HARNESS · AI score | `0.63925` | `0.63925` | `0.0` |
| Sub-pillar INNOVATE · Investments and Startups score | `0.6676666666666667` | `0.6676666666666667` | `0.0` |
| Sub-pillar INNOVATE · Other Emerging Technology score | `0.6514285714285714` | `0.6514285714285714` | `0.0` |
| Sub-pillar INNOVATE · AI score | `0.5873333333333333` | `0.5873333333333333` | `0.0` |
| Sub-pillar PROTECT · Preparedness score | `0.5955` | `0.5955` | `0.0` |
| Sub-pillar PROTECT · Risk of Attack score | `0.3993333333333334` | `0.3993333333333334` | `0.0` |
| Sub-pillar PROTECT · AI score | `0.6776666666666669` | `0.6776666666666669` | `0.0` |
| Sub-pillar SUSTAINABILITY · Sustainability score | `0.4843333333333334` | `0.4843333333333334` | `0.0` |
| Overall rank | `3.0` | `3.0` | `0.0` |
| Pillar rank CONNECT | `3.0` | `3.0` | `0.0` |
| Pillar rank HARNESS | `3.0` | `3.0` | `0.0` |
| Pillar rank INNOVATE | `4.0` | `4.0` | `0.0` |
| Pillar rank PROTECT | `6.0` | `6.0` | `0.0` |
| Pillar rank SUSTAINABILITY | `42.0` | `42.0` | `0.0` |
| Sub-pillar rank CONNECT · Affordability | `19.0` | `19.0` | `0.0` |
| Sub-pillar rank CONNECT · Quality | `46.0` | `46.0` | `0.0` |
| Sub-pillar rank CONNECT · Access | `2.0` | `2.0` | `0.0` |
| Sub-pillar rank CONNECT · AI | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank HARNESS · Apps and platform | `2.0` | `2.0` | `0.0` |
| Sub-pillar rank HARNESS · Data Intensity | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank HARNESS · Fintech | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank HARNESS · Real Economy | `2.0` | `2.0` | `0.0` |
| Sub-pillar rank HARNESS · AI | `7.0` | `7.0` | `0.0` |
| Sub-pillar rank INNOVATE · Investments and Startups | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank INNOVATE · Other Emerging Technology | `3.0` | `3.0` | `0.0` |
| Sub-pillar rank INNOVATE · AI | `5.0` | `5.0` | `0.0` |
| Sub-pillar rank PROTECT · Preparedness | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank PROTECT · Risk of Attack | `64.0` | `64.0` | `0.0` |
| Sub-pillar rank PROTECT · AI | `7.0` | `7.0` | `0.0` |
| Sub-pillar rank SUSTAINABILITY · Sustainability | `42.0` | `42.0` | `0.0` |

#### Sample indicators

| Indicator | Raw (exported) | Raw (engine) | delta raw | Score (exported) | Score (engine) | delta score |
| --- | --- | --- | --- | --- | --- | --- |
| Number of internet users | `803000000.0` | `803000000.0` | `0.0` | `0.985` | `0.985` | `0.0` |
| Median Mobile Download Speeds (Mbps) | `132.0` | `132.0` | `0.0` | `0.517` | `0.517` | `0.0` |
| E-commerce users | `392.7` | `392.7` | `0.0` | `0.9279999999999999` | `0.9279999999999999` | `0.0` |

### Brazil (`BRA`)

#### Headline and pillars

| Measure | Exported | Engine | delta |
| --- | --- | --- | --- |
| Overall CHIPS score | `0.5543` | `0.5543` | `0.0` |
| Pillar CONNECT | `0.6527083333333334` | `0.6527083333333334` | `0.0` |
| Pillar HARNESS | `0.5677000000000001` | `0.5677000000000001` | `0.0` |
| Pillar INNOVATE | `0.48903968253968255` | `0.48903968253968255` | `0.0` |
| Pillar PROTECT | `0.4877222222222223` | `0.4877222222222223` | `0.0` |
| Pillar SUSTAINABILITY | `0.5280000000000001` | `0.5280000000000001` | `0.0` |
| Sub-pillar CONNECT · Affordability score | `0.66525` | `0.66525` | `0.0` |
| Sub-pillar CONNECT · Quality score | `0.7155` | `0.7155` | `0.0` |
| Sub-pillar CONNECT · Access score | `0.62075` | `0.62075` | `0.0` |
| Sub-pillar CONNECT · AI score | `0.6093333333333335` | `0.6093333333333335` | `0.0` |
| Sub-pillar HARNESS · Apps and platform score | `0.6185` | `0.6185` | `0.0` |
| Sub-pillar HARNESS · Data Intensity score | `0.5035000000000001` | `0.5035000000000001` | `0.0` |
| Sub-pillar HARNESS · Fintech score | `0.597` | `0.597` | `0.0` |
| Sub-pillar HARNESS · Real Economy score | `0.5690000000000001` | `0.5690000000000001` | `0.0` |
| Sub-pillar HARNESS · AI score | `0.5505` | `0.5505` | `0.0` |
| Sub-pillar INNOVATE · Investments and Startups score | `0.4706666666666667` | `0.4706666666666667` | `0.0` |
| Sub-pillar INNOVATE · Other Emerging Technology score | `0.5582857142857143` | `0.5582857142857143` | `0.0` |
| Sub-pillar INNOVATE · AI score | `0.43816666666666665` | `0.43816666666666665` | `0.0` |
| Sub-pillar PROTECT · Preparedness score | `0.49550000000000005` | `0.49550000000000005` | `0.0` |
| Sub-pillar PROTECT · Risk of Attack score | `0.35366666666666674` | `0.35366666666666674` | `0.0` |
| Sub-pillar PROTECT · AI score | `0.6140000000000001` | `0.6140000000000001` | `0.0` |
| Sub-pillar SUSTAINABILITY · Sustainability score | `0.5280000000000001` | `0.5280000000000001` | `0.0` |
| Overall rank | `7.0` | `7.0` | `0.0` |
| Pillar rank CONNECT | `4.0` | `4.0` | `0.0` |
| Pillar rank HARNESS | `7.0` | `7.0` | `0.0` |
| Pillar rank INNOVATE | `13.0` | `13.0` | `0.0` |
| Pillar rank PROTECT | `47.0` | `47.0` | `0.0` |
| Pillar rank SUSTAINABILITY | `6.0` | `6.0` | `0.0` |
| Sub-pillar rank CONNECT · Affordability | `8.0` | `8.0` | `0.0` |
| Sub-pillar rank CONNECT · Quality | `8.0` | `8.0` | `0.0` |
| Sub-pillar rank CONNECT · Access | `5.0` | `5.0` | `0.0` |
| Sub-pillar rank CONNECT · AI | `12.0` | `12.0` | `0.0` |
| Sub-pillar rank HARNESS · Apps and platform | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank HARNESS · Data Intensity | `13.0` | `13.0` | `0.0` |
| Sub-pillar rank HARNESS · Fintech | `4.0` | `4.0` | `0.0` |
| Sub-pillar rank HARNESS · Real Economy | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank HARNESS · AI | `16.0` | `16.0` | `0.0` |
| Sub-pillar rank INNOVATE · Investments and Startups | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank INNOVATE · Other Emerging Technology | `9.0` | `9.0` | `0.0` |
| Sub-pillar rank INNOVATE · AI | `29.0` | `29.0` | `0.0` |
| Sub-pillar rank PROTECT · Preparedness | `11.0` | `11.0` | `0.0` |
| Sub-pillar rank PROTECT · Risk of Attack | `69.0` | `69.0` | `0.0` |
| Sub-pillar rank PROTECT · AI | `13.0` | `13.0` | `0.0` |
| Sub-pillar rank SUSTAINABILITY · Sustainability | `6.0` | `6.0` | `0.0` |

#### Sample indicators

| Indicator | Raw (exported) | Raw (engine) | delta raw | Score (exported) | Score (engine) | delta score |
| --- | --- | --- | --- | --- | --- | --- |
| Number of internet users | `182000000.0` | `182000000.0` | `0.0` | `0.653` | `0.653` | `0.0` |
| Median Mobile Download Speeds (Mbps) | `260.0` | `260.0` | `0.0` | `0.772` | `0.772` | `0.0` |
| E-commerce users | `166.1` | `166.1` | `0.0` | `0.708` | `0.708` | `0.0` |

### Costa Rica (`CRI`)

#### Headline and pillars

| Measure | Exported | Engine | delta |
| --- | --- | --- | --- |
| Overall CHIPS score | `0.44549999999999995` | `0.44549999999999995` | `0.0` |
| Pillar CONNECT | `0.4395` | `0.4395` | `0.0` |
| Pillar HARNESS | `0.413875` | `0.413875` | `0.0` |
| Pillar INNOVATE | `0.4193` | `0.4193` | `0.0` |
| Pillar PROTECT | `0.5090000000000001` | `0.5090000000000001` | `0.0` |
| Pillar SUSTAINABILITY | `0.50925` | `0.50925` | `0.0` |
| Sub-pillar CONNECT · Affordability score | `0.5495` | `0.5495` | `0.0` |
| Sub-pillar CONNECT · Quality score | `0.4385` | `0.4385` | `0.0` |
| Sub-pillar CONNECT · Access score | `0.407` | `0.407` | `0.0` |
| Sub-pillar CONNECT · AI score | `0.363` | `0.363` | `0.0` |
| Sub-pillar HARNESS · Apps and platform score | `0.414` | `0.414` | `0.0` |
| Sub-pillar HARNESS · Data Intensity score | `0.42900000000000005` | `0.42900000000000005` | `0.0` |
| Sub-pillar HARNESS · Fintech score | `0.4285` | `0.4285` | `0.0` |
| Sub-pillar HARNESS · Real Economy score | `0.384` | `0.384` | `0.0` |
| Sub-pillar HARNESS · AI score | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar INNOVATE · Investments and Startups score | `0.43799999999999994` | `0.43799999999999994` | `0.0` |
| Sub-pillar INNOVATE · Other Emerging Technology score | `0.4006` | `0.4006` | `0.0` |
| Sub-pillar INNOVATE · AI score | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar PROTECT · Preparedness score | `0.44799999999999995` | `0.44799999999999995` | `0.0` |
| Sub-pillar PROTECT · Risk of Attack score | `0.5700000000000002` | `0.5700000000000002` | `0.0` |
| Sub-pillar PROTECT · AI score | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar SUSTAINABILITY · Sustainability score | `0.50925` | `0.50925` | `0.0` |
| Overall rank | `51.0` | `51.0` | `0.0` |
| Pillar rank CONNECT | `51.0` | `51.0` | `0.0` |
| Pillar rank HARNESS | `62.0` | `62.0` | `0.0` |
| Pillar rank INNOVATE | `54.0` | `54.0` | `0.0` |
| Pillar rank PROTECT | `25.0` | `25.0` | `0.0` |
| Pillar rank SUSTAINABILITY | `10.0` | `10.0` | `0.0` |
| Sub-pillar rank CONNECT · Affordability | `31.0` | `31.0` | `0.0` |
| Sub-pillar rank CONNECT · Quality | `40.0` | `40.0` | `0.0` |
| Sub-pillar rank CONNECT · Access | `69.0` | `69.0` | `0.0` |
| Sub-pillar rank CONNECT · AI | `60.0` | `60.0` | `0.0` |
| Sub-pillar rank HARNESS · Apps and platform | `68.0` | `68.0` | `0.0` |
| Sub-pillar rank HARNESS · Data Intensity | `61.0` | `61.0` | `0.0` |
| Sub-pillar rank HARNESS · Fintech | `65.0` | `65.0` | `0.0` |
| Sub-pillar rank HARNESS · Real Economy | `59.0` | `59.0` | `0.0` |
| Sub-pillar rank HARNESS · AI | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar rank INNOVATE · Investments and Startups | `64.0` | `64.0` | `0.0` |
| Sub-pillar rank INNOVATE · Other Emerging Technology | `68.0` | `68.0` | `0.0` |
| Sub-pillar rank INNOVATE · AI | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar rank PROTECT · Preparedness | `57.0` | `57.0` | `0.0` |
| Sub-pillar rank PROTECT · Risk of Attack | `8.0` | `8.0` | `0.0` |
| Sub-pillar rank PROTECT · AI | `null` | `null` | `0.0 (null on both sides)` |
| Sub-pillar rank SUSTAINABILITY · Sustainability | `10.0` | `10.0` | `0.0` |

#### Sample indicators

| Indicator | Raw (exported) | Raw (engine) | delta raw | Score (exported) | Score (engine) | delta score |
| --- | --- | --- | --- | --- | --- | --- |
| Number of internet users | `4477274.0` | `4477274.0` | `0.0` | `0.408` | `0.408` | `0.0` |
| Median Mobile Download Speeds (Mbps) | `71.0` | `71.0` | `0.0` | `0.38299999999999995` | `0.38299999999999995` | `0.0` |
| E-commerce users | `1.8` | `1.8` | `0.0` | `0.42` | `0.42` | `0.0` |

## Result

Every delta above is exactly `0.0`. The exporter adds no rounding, no
rescaling and no reweighting of its own: leaf scores are the engine's
rounded 1-dp-on-0-100 values, pillar scores and coverage are full
precision, and the overall score keeps the engine's 2-dp rounding.

Sub-pillar ranks are compared at zero tolerance too: the exported `rank`
is checked against the same rule applied to the engine's own sub-pillar
scores (2 dp on the 0-100 scale, `rank(ascending=False, method="min")`,
non-present sub-pillars excluded).

Checked values: 2 methods x 3 countries x 50 measures = 300 comparisons, all zero.
