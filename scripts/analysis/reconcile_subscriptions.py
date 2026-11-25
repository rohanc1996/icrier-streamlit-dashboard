#!/usr/bin/env python3
"""Reconcile the two ITU subscription extracts used as 2027 denominators.

Question: for every SIDE country, does the value in
``data/reference/Mobile-cellular subscriptions.csv`` agree with the
``Mobile Cellular Subscriptions in millions (absolute numbers)`` column of
``data/SIDE 2027 - Absolute.csv``, once both are read for the same year?

Why this is not a tautology
---------------------------
The Absolute column is *derived*: ``build_itu_csv.py`` multiplies ITU's
*per 100 inhabitants* rate by UN DESA population for the year the rate refers
to. The reference CSV holds ITU's *reported* subscription totals. ITU's own
rate and its own total are not always consistent with each other, so the two
series disagree for a handful of countries. The ``Mobile data year`` column of
``data/2027 individual indicators/itu-transposed.csv`` says which year each
country's Absolute value refers to; that is the year both sides are compared at.

Fixed broadband has no counterpart in the Absolute file, so for that series the
script reports coverage and which countries need a carry-back instead.

Output: ``data/derived/subscription_denominator_reconciliation.csv``.

Run:  python scripts/analysis/reconcile_subscriptions.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "SIDE_dashboard"))

from core.loader import parse_numeric  # noqa: E402

ABSOLUTE = ROOT / "data" / "SIDE 2027 - Absolute.csv"
MOBILE_REF = ROOT / "data" / "reference" / "Mobile-cellular subscriptions.csv"
FIXED_REF = ROOT / "data" / "reference" / "Fixed-broadband subscriptions.csv"
ITU_SHEET = ROOT / "data" / "2027 individual indicators" / "itu-transposed.csv"
OUT = ROOT / "data" / "derived" / "subscription_denominator_reconciliation.csv"

MOBILE_ABS_COLUMN = "Mobile Cellular Subscriptions in millions (absolute numbers)"
MOBILE_DATA_YEAR = "Mobile data year"
TARGET_YEAR = "2025"

# The extracts use three ITU spellings that differ from the SIDE 2027 Absolute
# file. Everything else matches exactly.
ALIASES = {
    "Czech Republic": "Czechia",
    "Dominican Rep.": "Dominican Republic",
    "Korea (Rep. of)": "Republic of Korea",
    "United States": "United States of America",
}


def _tidy_name(name: str) -> str:
    return ALIASES.get(name.strip(), name.strip())


def load_reference(path: Path) -> dict[str, dict[str, float]]:
    """Return ``{SIDE country: {year: value}}`` for a wide ITU extract.

    Blank and ``-`` cells are dropped rather than read as zero.
    """
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw.columns = [str(c).strip() for c in raw.columns]
    country_column = raw.columns[0]
    years = [c for c in raw.columns[1:] if c.strip()]
    matrix = {year: parse_numeric(raw[year]) for year in years}
    series: dict[str, dict[str, float]] = {}
    for index, name in enumerate(raw[country_column]):
        values = {
            year: float(matrix[year].iloc[index])
            for year in years
            if pd.notna(matrix[year].iloc[index])
        }
        series[_tidy_name(name)] = values
    return series


def load_absolute() -> tuple[list[str], dict[str, float]]:
    raw = pd.read_csv(ABSOLUTE, dtype=str, keep_default_na=False)
    counts = parse_numeric(raw[MOBILE_ABS_COLUMN])
    countries: list[str] = []
    values: dict[str, float] = {}
    for name, number in zip(raw["Country"], counts):
        if not str(name).strip() or pd.isna(number):
            continue
        countries.append(str(name).strip())
        values[str(name).strip()] = float(number)
    return countries, values


def load_data_years() -> dict[str, str]:
    with ITU_SHEET.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = [cell.strip() for cell in next(reader)]
        countries = [cell.strip() for cell in header[1:]]
        for row in reader:
            if row and row[0].strip() == MOBILE_DATA_YEAR:
                return {
                    country: cell.strip()
                    for country, cell in zip(countries, row[1:])
                    if cell.strip()
                }
    raise SystemExit(f"{MOBILE_DATA_YEAR} not found in {ITU_SHEET}")


def latest(series: dict[str, float], up_to: str = TARGET_YEAR) -> tuple[str, float] | None:
    years = sorted(year for year in series if year <= up_to)
    if not years:
        return None
    year = years[-1]
    return year, series[year]


def main() -> int:
    countries, absolute = load_absolute()
    mobile = load_reference(MOBILE_REF)
    fixed = load_reference(FIXED_REF)
    data_years = load_data_years()

    records: list[dict[str, object]] = []
    missing_reference: list[str] = []
    differ: list[tuple[str, str, float, float]] = []

    for country in countries:
        year = data_years.get(country)
        reference = mobile.get(country, {})
        if year is None:
            status, ref_value = "no data year", None
        elif year not in reference:
            status, ref_value = "no reference value for data year", None
            missing_reference.append(country)
        else:
            ref_value = reference[year]
            delta = ref_value - absolute[country]
            status = "match" if abs(delta) < 1e-6 else ("rounding (±1)" if abs(delta) <= 1 else "differs")
            if status == "differs":
                differ.append((country, year, ref_value, absolute[country]))
        records.append(
            {
                "Series": "Mobile cellular subscriptions",
                "Country": country,
                "SIDE_2027_value": f"{absolute[country]:.0f}",
                "Data_year": year or "",
                "Reference_value": "" if ref_value is None else f"{ref_value:.0f}",
                "Delta": "" if ref_value is None else f"{ref_value - absolute[country]:.0f}",
                "Delta_pct": ""
                if ref_value is None
                else f"{(ref_value - absolute[country]) / absolute[country] * 100:.3f}",
                "Status": status,
            }
        )

    fixed_carry_back: list[tuple[str, str]] = []
    for country in countries:
        found = latest(fixed.get(country, {}))
        if found is None:
            year, value = "", None
            status = "no value"
        else:
            year, value = found
            status = "2025" if year == TARGET_YEAR else f"carry-back from {year}"
            if year != TARGET_YEAR:
                fixed_carry_back.append((country, year))
        records.append(
            {
                "Series": "Fixed broadband subscriptions",
                "Country": country,
                "SIDE_2027_value": "",
                "Data_year": year,
                "Reference_value": "" if value is None else f"{value:.0f}",
                "Delta": "",
                "Delta_pct": "",
                "Status": status,
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    matched = sum(1 for r in records if r["Status"] in {"match", "rounding (±1)"})
    print(f"Wrote {OUT.relative_to(ROOT)}  ({len(records)} rows)")
    print(f"  Mobile: {matched}/{len(countries)} agree with the 2027 Absolute value")
    print(f"  Mobile: no reference value for the data year: {missing_reference or 'none'}")
    for country, year, ref_value, side_value in differ:
        print(
            f"    differs: {country} {year} reference {ref_value:.0f} "
            f"vs Absolute {side_value:.0f} ({(ref_value - side_value) / side_value * 100:+.2f}%)"
        )
    print(f"  Fixed: {len(countries) - len(fixed_carry_back)}/71 at {TARGET_YEAR}")
    for country, year in fixed_carry_back:
        print(f"    carry-back: {country} -> {year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
