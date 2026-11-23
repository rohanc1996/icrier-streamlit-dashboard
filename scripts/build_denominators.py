#!/usr/bin/env python3
"""Build ``data/denominators.csv`` — the denominator table for the 2027
relative series.

One row per SIDE country (71), in ``data/SIDE 2027 - Absolute.csv`` order.

Columns
-------
``Country``          Canonical SIDE country name.
``GNI_pc_USD``       GNI per capita, Atlas method, current US$ for 2025.
                     **Two exceptions:** Kuwait (41,110) and the UAE
                     (51,550) use their last observation, 2024, because WDI
                     has no 2025 value.  This file carries no year column, so
                     those two rows are not distinguishable on its face; see
                     "Known gaps" below.
``Listed_companies`` Listed domestic companies, total (CM.MKT.LDOM.NO) for
                     2025.  **Empty for 25 of the 71 countries** — 6 never
                     report in the WDI series and 19 have a stale latest
                     observation.  No back-filling is done here.
``GDP_2025_USD``     Nominal GDP 2025, current US$, via ``gdp_reference``.
``Population_2025``  Total population 2025 from UN DESA WPP 2024 (Medium
                     variant), via the ITU population cache.

Sources
-------
- ``data/reference/WB GNI per capita by year.csv``      (NY.GNP.PCAP.CD)
- ``data/reference/WB listed company counts by year.csv`` (CM.MKT.LDOM.NO)
- ``data/reference/GDP data for SIDE 2027.xlsx - side subset USD.csv``
- ``scripts/data_sources/itu/cache/undes_population.json``

Known gaps (2025 coverage)
--------------------------
GNI per capita: 69/71 at 2025 (Kuwait and UAE at 2024).
Listed companies: 46/71 at 2025.
   Never reported: Algeria, Dominican Republic, Ethiopia, Guatemala, Iraq,
   Serbia.
   Stale latest: Argentina (2021), Belgium (2015), Costa Rica (2022),
   Denmark (2004), Ecuador (2000), Finland (2004), France (2018),
   Ireland (2018), Israel (2024), Italy (2014), Mexico (2023),
   Netherlands (2018), Norway (2017), Portugal (2018), Russian Federation
   (2023), Slovakia (2013), Sweden (2002), Ukraine (2018), United Kingdom
   (2022).

Run:  python scripts/build_denominators.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "data_sources" / "itu"))

from fetch_undes import ISO3  # noqa: E402
from gdp_reference import gdp_usd  # noqa: E402

REFERENCE = ROOT / "data" / "reference"
ABSOLUTE = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "data" / "denominators.csv"

GNI_PATH = REFERENCE / "WB GNI per capita by year.csv"
LISTED_PATH = REFERENCE / "WB listed company counts by year.csv"
POP_CACHE = ROOT / "scripts" / "data_sources" / "itu" / "cache" / "undes_population.json"

GNI_YEAR = "2025"
LISTED_YEAR = "2025"
POP_YEAR = "2025"
GDP_YEAR = "2025"

# WDI uses its own country spellings for five SIDE countries.
WDI_ALIASES = {
    "Egypt": "Egypt, Arab Rep.",
    "Republic of Korea": "Korea, Rep.",
    "Slovakia": "Slovak Republic",
    "Türkiye": "Turkiye",
    "United States of America": "United States",
}

# The wide WDI extracts start with four metadata rows before the header.
WDI_METADATA_ROWS = 4

FIELDS = [
    "Country",
    "GNI_pc_USD",
    "Listed_companies",
    "GDP_2025_USD",
    "Population_2025",
]


def side_countries() -> list[str]:
    with ABSOLUTE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [row["Country"].strip() for row in reader if row["Country"].strip()]


def load_wdi_wide(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    """Return (years, rows keyed by WDI country name) for a WDI wide extract."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = list(csv.reader(handle))
    header = reader[WDI_METADATA_ROWS]
    years = [cell.strip() for cell in header[4:] if cell.strip()]
    rows: dict[str, list[str]] = {}
    for row in reader[WDI_METADATA_ROWS + 1 :]:
        if not row or not row[0].strip():
            continue
        rows[row[0].strip()] = row[4:]
    return years, rows


def value_for(
    name: str,
    preferred_year: str,
    years: list[str],
    rows: dict[str, list[str]],
    allow_fallback: bool = True,
) -> tuple[str, float | None]:
    """Return (year_of_value, value) — preferred year, else the latest available.

    With ``allow_fallback=False`` only the preferred year counts, so a stale
    series reads as blank rather than as a mismatched vintage.
    An empty value with no observation at all returns ("", None).
    """
    row = rows[WDI_ALIASES.get(name, name)]
    index = years.index(preferred_year)
    preferred = row[index].strip() if index < len(row) else ""
    if preferred:
        return preferred_year, float(preferred)
    if not allow_fallback:
        return "", None
    latest: tuple[str, float] | None = None
    for year, cell in zip(years, row):
        text = cell.strip()
        if text:
            latest = (year, float(text))
    return latest if latest is not None else ("", None)


def as_int(value: float | None) -> str:
    if value is None:
        return ""
    rounded = round(value)
    if abs(value - rounded) < 1e-6:
        return str(int(rounded))
    return repr(value)


def main() -> int:
    countries = side_countries()
    gni_years, gni_rows = load_wdi_wide(GNI_PATH)
    listed_years, listed_rows = load_wdi_wide(LISTED_PATH)
    population = json.loads(POP_CACHE.read_text(encoding="utf-8"))

    records: list[dict[str, str]] = []
    gni_carried_back: list[tuple[str, str, float]] = []
    listed_blank: list[str] = []

    for country in countries:
        gni_year, gni_value = value_for(country, GNI_YEAR, gni_years, gni_rows)
        if gni_year != GNI_YEAR:
            gni_carried_back.append((country, gni_year, gni_value or 0.0))

        listed_year, listed_value = value_for(
            country, LISTED_YEAR, listed_years, listed_rows, allow_fallback=False
        )
        if listed_year != LISTED_YEAR:
            listed_blank.append(country)

        gdp = gdp_usd(country, GDP_YEAR)
        pop = population.get(ISO3[country], {}).get(POP_YEAR)

        records.append(
            {
                "Country": country,
                "GNI_pc_USD": as_int(gni_value),
                "Listed_companies": as_int(listed_value),
                "GDP_2025_USD": as_int(gdp),
                "Population_2025": as_int(pop),
            }
        )

    _validate(records, countries, listed_blank)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {OUT.relative_to(ROOT)}  ({len(records)} rows)")
    print(f"  GNI per capita {GNI_YEAR}: {len(records) - len(gni_carried_back)}/71")
    for country, year, value in gni_carried_back:
        print(f"    carried back: {country} -> {year} {as_int(value)}")
    print(f"  Listed companies {LISTED_YEAR}: {len(records) - len(listed_blank)}/71")
    print(f"    blank for {len(listed_blank)} countries: {', '.join(listed_blank)}")
    return 0


def _validate(
    records: list[dict[str, str]],
    countries: list[str],
    listed_blank: list[str],
) -> None:
    assert len(records) == 71, f"expected 71 rows, got {len(records)}"
    assert [r["Country"] for r in records] == countries, "country order drifted"
    for row in records:
        assert row["Country"], "empty country name"
        assert row["GNI_pc_USD"], f"missing GNI per capita for {row['Country']}"
        assert row["GDP_2025_USD"], f"missing GDP for {row['Country']}"
        assert row["Population_2025"], f"missing population for {row['Country']}"
    populated = sum(1 for r in records if r["Listed_companies"])
    assert populated == 46, f"expected 46 listed-company values, got {populated}"
    assert len(listed_blank) == 25, f"expected 25 blanks, got {len(listed_blank)}"


if __name__ == "__main__":
    raise SystemExit(main())
