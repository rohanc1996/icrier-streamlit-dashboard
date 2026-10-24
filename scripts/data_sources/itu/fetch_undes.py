#!/usr/bin/env python3
"""Fetch UN DESA World Population Prospects 2024 total population.

Source: WPP 2024 bulk download, ``WPP2024_TotalPopulationBySex.csv.gz``
        https://population.un.org/wpp/assets/Excel%20Files/1_Indicator%20(Standard)/CSV_FILES/WPP2024_TotalPopulationBySex.csv.gz

The file reports ``PopTotal`` in thousands. Values are cached as persons for
the medium variant, both sexes. Only the 71 SIDE countries and recent years are
kept; the 17 MB source file is not cached.

Run:  python scripts/data_sources/itu/fetch_undes.py
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import urllib.request
from pathlib import Path

URL = (
    "https://population.un.org/wpp/assets/Excel%20Files/"
    "1_Indicator%20(Standard)/CSV_FILES/WPP2024_TotalPopulationBySex.csv.gz"
)
CACHE = Path(__file__).resolve().parent / "cache" / "undes_population.json"

ISO3 = {
    "Algeria": "DZA", "Argentina": "ARG", "Australia": "AUS", "Austria": "AUT",
    "Bangladesh": "BGD", "Belgium": "BEL", "Brazil": "BRA", "Bulgaria": "BGR",
    "Canada": "CAN", "Chile": "CHL", "China": "CHN", "Colombia": "COL",
    "Costa Rica": "CRI", "Croatia": "HRV", "Czechia": "CZE", "Denmark": "DNK",
    "Dominican Republic": "DOM", "Ecuador": "ECU", "Egypt": "EGY",
    "Ethiopia": "ETH", "Finland": "FIN", "France": "FRA", "Germany": "DEU",
    "Ghana": "GHA", "Greece": "GRC", "Guatemala": "GTM", "Hungary": "HUN",
    "India": "IND", "Indonesia": "IDN", "Iraq": "IRQ", "Ireland": "IRL",
    "Israel": "ISR", "Italy": "ITA", "Japan": "JPN", "Kazakhstan": "KAZ",
    "Kenya": "KEN", "Kuwait": "KWT", "Malaysia": "MYS", "Mexico": "MEX",
    "Morocco": "MAR", "Netherlands": "NLD", "New Zealand": "NZL",
    "Nigeria": "NGA", "Norway": "NOR", "Pakistan": "PAK", "Peru": "PER",
    "Philippines": "PHL", "Poland": "POL", "Portugal": "PRT", "Qatar": "QAT",
    "Republic of Korea": "KOR", "Romania": "ROU", "Russian Federation": "RUS",
    "Rwanda": "RWA", "Saudi Arabia": "SAU", "Serbia": "SRB",
    "Singapore": "SGP", "Slovakia": "SVK", "South Africa": "ZAF",
    "Spain": "ESP", "Sri Lanka": "LKA", "Sweden": "SWE", "Switzerland": "CHE",
    "Thailand": "THA", "Türkiye": "TUR", "Ukraine": "UKR",
    "United Arab Emirates": "ARE", "United Kingdom": "GBR",
    "United States of America": "USA", "Uzbekistan": "UZB", "Viet Nam": "VNM",
}
ISO_CODES = set(ISO3.values())
MIN_YEAR = 2015


def fetch(use_cache: bool = True) -> dict[str, dict[str, float]]:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        raw = gzip.decompress(resp.read())
    text = raw.decode("utf-8-sig", "ignore")

    population: dict[str, dict[str, float]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("Variant") != "Medium":
            continue
        iso = row.get("ISO3_code")
        if iso not in ISO_CODES:
            continue
        try:
            year = int(row["Time"])
            thousands = float(row["PopTotal"])
        except (KeyError, TypeError, ValueError):
            continue
        if year < MIN_YEAR or thousands <= 0:
            continue
        population.setdefault(iso, {})[str(year)] = thousands * 1000

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(population, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return population


def main() -> int:
    data = fetch(use_cache=False)
    print(f"Cached {CACHE} ({len(data)} countries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
