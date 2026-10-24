#!/usr/bin/env python3
"""Build the transposed Tortoise AI Infrastructure CSV.

Output: data/tortoise-ai-infrastructure-transposed.csv

Layout matches ``speedtest-transposed.csv``: the first column is ``Indicator``
and the remaining columns are the 71 SIDE countries, in SIDE order. Countries
absent from the Tortoise index are filled with ``-``.

Run:  python scripts/data_sources/tortoise/build_tortoise_csv.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_tortoise_ai import fetch  # noqa: E402

COUNTRY_REF = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "data" / "tortoise-ai-infrastructure-transposed.csv"
INDICATOR = "AI Infrastructure Score (2025)"

# Tortoise country label -> SIDE country name.
ALIASES = {
    "Czech Rep.": "Czechia",
    "Dominican Rep.": "Dominican Republic",
    "South Korea": "Republic of Korea",
    "Russia": "Russian Federation",
    "Turkey": "Türkiye",
    "UAE": "United Arab Emirates",
    "UK": "United Kingdom",
    "US": "United States of America",
    "Vietnam": "Viet Nam",
}


def side_countries() -> list[str]:
    with COUNTRY_REF.open(newline="", encoding="utf-8") as fh:
        return [
            row[0]
            for row in list(csv.reader(fh))[1:]
            if row and row[0] and row[0] != "Coefficient of variation"
        ]


def main() -> int:
    data = fetch(use_cache=True)
    tortoise = {
        ALIASES.get(country, country): score
        for country, score in data["scores"].items()
    }
    countries = side_countries()

    values = [str(tortoise[c]) if c in tortoise else "-" for c in countries]

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Indicator"] + countries)
        writer.writerow([INDICATOR] + values)

    missing = [c for c in countries if c not in tortoise]
    print(
        f"Wrote {OUT} ({len(countries)} countries, "
        f"{len(countries) - len(missing)} scored, missing: {', '.join(missing) or 'none'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
