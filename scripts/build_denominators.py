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
                     2025, from ``data/derived/listed_companies_2025_estimates.csv``.
                     That file reports the 46 WDI observations as-is and fills
                     the 19 stale countries from exchange/WFE/regulator
                     sources; carry-forward is only a fallback where no
                     exchange figure exists (none needed for 2025). See
                     ``docs/decisions/0001-listed-companies-2025.md``.
                     ``Listed_companies_method`` records which of ``reported``
                     / ``carry_forward`` / ``exchange`` / ``missing`` applies,
                     and ``Listed_companies_source_year`` the year the value
                     actually refers to.  Six never-reporting countries stay
                     blank.
``Startups_tracxn``  Total number of startups, Tracxn snapshot supplied for the
                     2027 edition. This is the denominator for the Relative
                     series' "Total funding ... per startup" indicator (and the
                     same count is the numerator of "Start-ups per limited
                     liability company"). It is asserted to equal the
                     ``Number of Start-ups`` column of
                     ``data/SIDE 2027 - Absolute.csv`` so the absolute and
                     relative series cannot drift apart.
``Labour_force_2025`` Total labour force, thousands. Source is WDI
                     ``SL.TLF.TOTL.IN``, which is the ILO **modelled**
                     estimates rebased onto World Bank population — the same
                     series the 2026 Relative ``ICT sector employment (% of
                     Total Labour force)`` column was built from. 70/71 at
                     2025; Ukraine is carried back to its last observation
                     (2021) because WDI has nothing after the invasion.
                     ``Labour_force_source_year`` records the year the value
                     actually refers to.
``GDP_2025_USD``     Nominal GDP 2025, current US$, via ``gdp_reference``.
``Population_2025``  Total population 2025 from UN DESA WPP 2024 (Medium
                     variant), via the ITU population cache.
``Internet_users_2025``  Number of internet users, count (not per 100), for
                     2025. Copied verbatim from the ``Number of Internet
                     Users (absolute numbers)`` column of
                     ``data/SIDE 2027 - Absolute.csv``. This is the
                     denominator of the Relative series' "% of internet
                     users" and "per internet user" indicators; the 2026
                     Relative file divides by exactly this column (ratio
                     1.0000 against all five "% of internet users" columns).
``Smartphone_users_2025``  Number of smartphone users, count (not millions).
                     Copied verbatim from the ``Number of smartphone users
                     (million)`` column of ``data/SIDE 2027 - Absolute.csv``,
                     which is **mislabelled**: despite the "(million)" suffix
                     it holds raw counts (India 816.6m, USA 235.5m). It is
                     the denominator of "AR/VR revenue per smartphone user"
                     and "Metaverse revenue per smartphone user". Those two
                     columns are additionally PPP-adjusted; that factor is
                     *not* in this file.

Sources
-------
- ``data/reference/WB GNI per capita by year.csv``      (NY.GNP.PCAP.CD)
- ``data/reference/WB listed company counts by year.csv`` (CM.MKT.LDOM.NO),
  via ``data/derived/listed_companies_2025_estimates.csv``
- ``data/reference/tracxn startups counts.csv``
- ``data/reference/WB labour force by year.csv``           (SL.TLF.TOTL.IN)
- ``data/reference/GDP data for SIDE 2027.xlsx - side subset USD.csv``
- ``scripts/data_sources/itu/cache/undes_population.json``
- ``data/SIDE 2027 - Absolute.csv`` internet-user and smartphone-user columns

Known gaps (2025 coverage)
--------------------------
GNI per capita: 69/71 at 2025 (Kuwait and UAE at 2024).
Labour force: 70/71 at 2025; Ukraine at 2021 (WDI publishes nothing later).
Listed companies: 60/71 at 2025 once estimates are included — 46 reported
   and 14 from exchange/WFE/regulator sources.
   Never reported: Algeria, Dominican Republic, Ethiopia, Guatemala, Iraq,
   Serbia.
   No comparable 2025 figure found: Belgium, Ecuador, Netherlands, Portugal,
   Ukraine.

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
LISTED_ESTIMATES = ROOT / "data" / "derived" / "listed_companies_2025_estimates.csv"
STARTUPS_PATH = REFERENCE / "tracxn startups counts.csv"
LABOUR_PATH = REFERENCE / "WB labour force by year.csv"
POP_CACHE = ROOT / "scripts" / "data_sources" / "itu" / "cache" / "undes_population.json"

GNI_YEAR = "2025"
LISTED_YEAR = "2025"
POP_YEAR = "2025"
LABOUR_YEAR = "2025"
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
    "Listed_companies_method",
    "Listed_companies_source_year",
    "Startups_tracxn",
    "Labour_force_2025",
    "Labour_force_source_year",
    "GDP_2025_USD",
    "Population_2025",
    "Internet_users_2025",
    "Smartphone_users_2025",
]

INTERNET_USERS_COLUMN = "Number of Internet Users (absolute numbers)"
SMARTPHONE_USERS_COLUMN = "Number of smartphone users (million)"


def load_listed_estimates() -> dict[str, dict[str, str]]:
    """Return the 2025 listed-company table keyed by SIDE country name."""
    with LISTED_ESTIMATES.open(newline="", encoding="utf-8-sig") as handle:
        return {row["Country"].strip(): row for row in csv.DictReader(handle)}


def load_tracxn() -> dict[str, str]:
    """Return the Tracxn startup counts keyed by SIDE country name.

    The source repeats its ``Country`` header, so it is read positionally:
    column 0 holds the canonical SIDE name, column 2 the count.
    """
    with STARTUPS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.reader(handle)
        next(rows)
        return {
            row[0].strip(): row[2].strip()
            for row in rows
            if row and row[0].strip()
        }


def side_countries() -> list[str]:
    with ABSOLUTE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return [row["Country"].strip() for row in reader if row["Country"].strip()]


def absolute_startups() -> dict[str, str]:
    """Return ``Number of Start-ups`` from the 2027 Absolute file, by country."""
    with ABSOLUTE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {
            row["Country"].strip(): row["Number of Start-ups"].strip()
            for row in reader
            if row["Country"].strip()
        }


def absolute_user_counts() -> dict[str, tuple[str, str]]:
    """Return (internet users, smartphone users) from the 2027 Absolute file.

    Both values are raw country counts. The smartphone column is labelled
    "(million)" in the source but holds counts; it is copied verbatim so the
    denominator equals the 2027 Absolute numerator of the same indicator.
    """
    with ABSOLUTE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {
            row["Country"].strip(): (
                row[INTERNET_USERS_COLUMN].strip(),
                row[SMARTPHONE_USERS_COLUMN].strip(),
            )
            for row in reader
            if row["Country"].strip()
        }


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
) -> tuple[str, float | None]:
    """Return (year_of_value, value) — preferred year, else the latest available.

    An empty value with no observation at all returns ("", None).
    """
    row = rows[WDI_ALIASES.get(name, name)]
    index = years.index(preferred_year)
    preferred = row[index].strip() if index < len(row) else ""
    if preferred:
        return preferred_year, float(preferred)
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


def as_thousands(value: float | None) -> str:
    """Convert a person count to thousands, keeping one decimal."""
    if value is None:
        return ""
    return as_int(round(value / 1000.0, 1))


def main() -> int:
    countries = side_countries()
    gni_years, gni_rows = load_wdi_wide(GNI_PATH)
    labour_years, labour_rows = load_wdi_wide(LABOUR_PATH)
    listed = load_listed_estimates()
    startups = load_tracxn()
    absolute_startups_by_country = absolute_startups()
    user_counts = absolute_user_counts()
    population = json.loads(POP_CACHE.read_text(encoding="utf-8"))

    records: list[dict[str, str]] = []
    gni_carried_back: list[tuple[str, str, float]] = []
    labour_carried_back: list[tuple[str, str, float]] = []
    listed_blank: list[str] = []

    for country in countries:
        gni_year, gni_value = value_for(country, GNI_YEAR, gni_years, gni_rows)
        if gni_year != GNI_YEAR:
            gni_carried_back.append((country, gni_year, gni_value or 0.0))

        labour_year, labour_value = value_for(
            country, LABOUR_YEAR, labour_years, labour_rows
        )
        if labour_year != LABOUR_YEAR:
            labour_carried_back.append((country, labour_year, labour_value or 0.0))

        entry = listed[country]
        listed_value = entry["Listed_companies_2025"].strip()
        if not listed_value:
            listed_blank.append(country)

        gdp = gdp_usd(country, GDP_YEAR)
        pop = population.get(ISO3[country], {}).get(POP_YEAR)
        internet_users, smartphone_users = user_counts[country]

        records.append(
            {
                "Country": country,
                "GNI_pc_USD": as_int(gni_value),
                "Listed_companies": listed_value,
                "Listed_companies_method": entry["Method"].strip(),
                "Listed_companies_source_year": entry["Source_year"].strip(),
                "Startups_tracxn": startups[country],
                "Labour_force_2025": as_thousands(labour_value),
                "Labour_force_source_year": labour_year,
                "GDP_2025_USD": as_int(gdp),
                "Population_2025": as_int(pop),
                "Internet_users_2025": internet_users,
                "Smartphone_users_2025": smartphone_users,
            }
        )

    _validate(
        records,
        countries,
        listed_blank,
        listed,
        absolute_startups_by_country,
        user_counts,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {OUT.relative_to(ROOT)}  ({len(records)} rows)")
    print(f"  GNI per capita {GNI_YEAR}: {len(records) - len(gni_carried_back)}/71")
    for country, year, value in gni_carried_back:
        print(f"    carried back: {country} -> {year} {as_int(value)}")
    print(f"  Labour force {LABOUR_YEAR}: {71 - len(labour_carried_back)}/71")
    for country, year, value in labour_carried_back:
        print(f"    carried back: {country} -> {year} {as_thousands(value)}")
    print(f"  Startups (Tracxn): {len(records)}/71 (matches 2027 Absolute)")
    print(f"  Internet users {INTERNET_USERS_COLUMN}: {len(records)}/71")
    print(f"  Smartphone users {SMARTPHONE_USERS_COLUMN}: {len(records)}/71")
    print(f"  Listed companies {LISTED_YEAR}: {71 - len(listed_blank)}/71")
    for method in ("reported", "carry_forward", "exchange", "missing"):
        count = sum(1 for r in records if r["Listed_companies_method"] == method)
        print(f"    {method}: {count}")
    print(f"    blank for {len(listed_blank)} countries: {', '.join(listed_blank)}")
    return 0


def _validate(
    records: list[dict[str, str]],
    countries: list[str],
    listed_blank: list[str],
    listed: dict[str, dict[str, str]],
    absolute_startups_by_country: dict[str, str],
    user_counts: dict[str, tuple[str, str]],
) -> None:
    assert len(records) == 71, f"expected 71 rows, got {len(records)}"
    assert [r["Country"] for r in records] == countries, "country order drifted"
    for row in records:
        assert row["Country"], "empty country name"
        assert row["GNI_pc_USD"], f"missing GNI per capita for {row['Country']}"
        assert row["GDP_2025_USD"], f"missing GDP for {row['Country']}"
        assert row["Population_2025"], f"missing population for {row['Country']}"
        labour = row["Labour_force_2025"]
        assert labour, f"missing labour force for {row['Country']}"
        labour_value = float(labour)
        assert labour_value > 0, f"non-positive labour force for {row['Country']}"
        ratio = labour_value * 1000.0 / float(row["Population_2025"])
        assert 0.20 <= ratio <= 0.80, (
            f"labour force for {row['Country']} is {ratio:.1%} of population"
        )
        value = row["Startups_tracxn"]
        assert value.isdigit() and int(value) > 0, (
            f"bad Tracxn startup count for {row['Country']}: {value!r}"
        )
        assert value == absolute_startups_by_country.get(row["Country"]), (
            f"Tracxn count for {row['Country']} disagrees with "
            f"the 2027 Absolute Number of Start-ups "
            f"({value} vs {absolute_startups_by_country.get(row['Country'])})"
        )

        internet = row["Internet_users_2025"]
        smartphone = row["Smartphone_users_2025"]
        assert internet.isdigit() and int(internet) > 0, (
            f"bad internet-user count for {row['Country']}: {internet!r}"
        )
        assert smartphone.isdigit() and int(smartphone) > 0, (
            f"bad smartphone-user count for {row['Country']}: {smartphone!r}"
        )
        assert (internet, smartphone) == user_counts[row["Country"]], (
            f"user counts for {row['Country']} drifted from the 2027 Absolute file"
        )
        internet_share = int(internet) / float(row["Population_2025"])
        assert 0.10 <= internet_share <= 1.02, (
            f"internet users for {row['Country']} is {internet_share:.1%} of population"
        )
        smartphone_share = int(smartphone) / int(internet)
        assert 0.25 <= smartphone_share <= 1.10, (
            f"smartphone users for {row['Country']} is "
            f"{smartphone_share:.1%} of internet users"
        )
    carried = [
        (row["Country"], row["Labour_force_source_year"])
        for row in records
        if row["Labour_force_source_year"] != LABOUR_YEAR
    ]
    assert carried == [("Ukraine", "2021")], (
        f"unexpected labour-force carry-backs: {carried}"
    )
    methods = {row["Listed_companies_method"] for row in records}
    assert methods <= {"reported", "carry_forward", "exchange", "missing"}, methods
    reported = sum(1 for r in records if r["Listed_companies_method"] == "reported")
    assert reported == 46, f"expected 46 reported listed-company values, got {reported}"
    missing = [r for r in records if r["Listed_companies_method"] == "missing"]
    never = [country for country in countries if not listed[country]["WDI_last_year"].strip()]
    assert len(never) == 6, f"expected 6 never-reporting countries, got {len(never)}"
    assert len(listed_blank) == len(missing), "blank count disagrees with method"
    for row in records:
        if row["Listed_companies_method"] == "missing":
            assert not row["Listed_companies"], f"{row['Country']} missing but has a value"
        else:
            assert row["Listed_companies"], f"no listed-company value for {row['Country']}"


if __name__ == "__main__":
    raise SystemExit(main())
