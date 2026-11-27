# Source panel — internet and smartphone users

`internet-smartphone-source-panel.csv`: 71 SIDE countries, users in millions,
one row per country, built by `scripts/analysis/build_source_panel.py`.

## Columns and sources

| Column | Source |
|---|---|
| `Population_2024_m`, `Population_2025_m` | UN DESA WPP 2024, via `scripts/data_sources/itu/cache/undes_population.json` |
| `Internet_Statista_2026_m` | `data/reference/statista 2026 Internet User Counts.csv` |
| `Internet_SIDE2026_report_m` | `Number of Internet Users (absolute numbers)`, `SIDE 2026 - Absolute.csv` |
| `Internet_ITU_2024_m`, `Internet_ITU_2025_m` | ITU DataHub indicator 11624 × UN DESA population for that year |
| `Internet_Findex_2024_totalpop_m` | Global Findex 2024, % of age 15+ × **total** population (2024) |
| `Smartphone_Statista_2026_m` | `data/2027 individual indicators/statista_2026 Smartphone Users by Country.csv` |
| `Smartphone_SIDE2026_report_m` | `Number of smartphone users (million)`, `SIDE 2026 - Absolute.csv` (raw counts despite the name) |
| `Smartphone_Findex_2024_m` | Findex 2024 shared + main smartphone use, as built by `build_smartphone_users_csv.py` |

ITU is not shown for smartphone users because ITU does not publish a
smartphone-user series. `Internet_ITU_2025_m` is blank for 38 countries where
the latest ITU value is still 2024.

## Population base

`Internet_Findex_2024_totalpop_m` applies the Findex rate to total population,
not to the 15+ population the survey actually covers. That is deliberate: SIDE
2026/2027 average the ITU total-population rate with the Findex 15+ rate and
then scale by total population, so this column is on the same base as the
report. Averaging `Internet_ITU_2024_m` and `Internet_Findex_2024_totalpop_m`
reproduces `Internet_SIDE2026_report_m` at a median absolute difference of
0.002% (Sri Lanka is the only outlier, at ~4.8%, because the 2026 report
appears to have used a different ITU vintage there).

`Smartphone_Findex_2024_m` stays on the 15+ base, because the smartphone series
averages a Statista count with Findex on 15+; it is not reconstituted here.

The demographically consistent internet count — Findex rate × 15+ population —
is about 9% lower than the column above (median across countries, range 4.9%
to 26.7%), and is not carried in this file.

## What the labels mean

**There is no Statista 2025 export in the repo.** The `SIDE2026_report` columns
are what the 2026 edition carried, not Statista 2025 values:

- Internet: the column reproduces `(ITU 2024 + Findex 2024) / 2` to within a
  median 0.0% across 68 countries (worst case Sri Lanka, 5%). It is not Statista.
- Smartphone: consistent with an average of an older Statista vintage and Findex;
  it moves with the 2026 Statista values at a median 4.4% but with much wider tails.

`SIDE 2025 - Absolute.csv` is not a usable Statista 2025 source: it has 59
countries under different names (`United States`, `Russia`, `Turkey`, …) and its
smartphone column is zero for 25 of them.

The Statista 2026 smartphone page has mixed provenance: of its 70 source links,
46 point to Statista *mobile internet users* pages and 23 to *smartphone users*
pages.

## Checks visible in the panel

- Statista 2026 internet tracks ITU 2024 at a median ratio of 1.03
  (p10–p90 0.99–1.13), a plausible one-year step.
- Statista 2026 smartphone against the SIDE 2026 report: median 1.15, but
  p10–p90 0.84–1.59.
- Seven countries have more Statista smartphone users than Statista internet
  users: Bangladesh, China, Ethiopia, India, Japan, Pakistan, Viet Nam.
  India is 1,052.7m phones against 1,040m internet users.

Run:

```bash
./.venv/bin/python scripts/analysis/build_source_panel.py
```

The ITU series is cached at
`scripts/data_sources/itu/cache/itu_internet_by_year.json`; delete it to refetch.
