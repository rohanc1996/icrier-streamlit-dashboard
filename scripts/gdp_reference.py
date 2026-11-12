#!/usr/bin/env python3
"""Canonical nominal-GDP reference used by the SIDE 2027 calculations.

Source: ``data/reference/GDP data for SIDE 2027.xlsx - side subset USD.csv``

The file is a CSV with World Bank country names, an ISO3 column whose header
is misleadingly ``GDP (current US$)``, and one column per year (2019-2025).
Values are nominal GDP in current US dollars.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = (
    ROOT / "data" / "reference" / "GDP data for SIDE 2027.xlsx - side subset USD.csv"
)

YEARS: tuple[str, ...] = ("2019", "2020", "2021", "2022", "2023", "2024", "2025")

COUNTRY_MAP = {
    "Egypt, Arab Rep.": "Egypt",
    "Korea, Rep.": "Republic of Korea",
    "Slovak Republic": "Slovakia",
    "Turkiye": "Türkiye",
    "United States": "United States of America",
}


@dataclass(frozen=True)
class GdpRecord:
    country: str
    iso3: str
    values: dict[str, float]


def _parse_number(text: str | None) -> float | None:
    if text is None:
        return None
    cleaned = str(text).strip().replace(",", "")
    if not cleaned:
        return None
    return float(cleaned)


def _canonical_country(name: str) -> str:
    cleaned = name.strip()
    return COUNTRY_MAP.get(cleaned, cleaned)


@lru_cache(maxsize=4)
def load_gdp_reference(path: str | Path = REFERENCE_PATH) -> dict[str, GdpRecord]:
    """Load nominal GDP by canonical SIDE country name."""
    source = Path(path)
    records: dict[str, GdpRecord] = {}
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            raw_country = (row.get("Country Name") or "").strip()
            if not raw_country:
                continue
            country = _canonical_country(raw_country)
            iso3 = (row.get("GDP (current US$)") or "").strip()
            values: dict[str, float] = {}
            for year in YEARS:
                value = _parse_number(row.get(year))
                if value is not None:
                    values[year] = value
            records[country] = GdpRecord(country=country, iso3=iso3, values=values)
    return records


def available_years() -> tuple[str, ...]:
    return YEARS


def gdp_usd(country: str, year: str) -> float | None:
    """Nominal GDP in current US dollars, or ``None`` when unavailable."""
    if year not in YEARS:
        raise ValueError(f"Unsupported GDP year {year!r}; expected one of {YEARS}")
    record = load_gdp_reference().get(country)
    if record is None:
        return None
    return record.values.get(year)


def share_of_gdp(
    value_usd: float | None,
    country: str,
    year: str,
    as_percent: bool = True,
) -> float | None:
    """Express a USD value as a share of the country's nominal GDP."""
    if value_usd is None:
        return None
    value = float(value_usd)
    if not math.isfinite(value):
        return None
    denominator = gdp_usd(country, year)
    if denominator is None or denominator <= 0:
        return None
    share = value / denominator
    return share * 100.0 if as_percent else share
