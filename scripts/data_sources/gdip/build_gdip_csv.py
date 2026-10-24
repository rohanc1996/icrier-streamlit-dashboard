#!/usr/bin/env python3
"""Build a transposed CSV from GDIP's public device-pricing data.

Source: https://globaldigitalinclusion.org/wp-content/uploads/2024/10/
        GDIP-Data-Device-Pricing-2024-Public.csv

GDIP publishes the cheapest smartphones and feature phones found on operator
websites. This script keeps the cheapest *smartphone* per country and exposes
the published USD price and affordability (% of monthly GNI per capita).

GDIP does not publish PPP-dollar device prices, so no PPP conversion is done
here. The 2024 file is the latest public country-level release.

Output: data/2027 individual indicators/gdip-smartphone-transposed.csv

Run:  python scripts/data_sources/gdip/build_gdip_csv.py
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))

from fetch_undes import ISO3  # noqa: E402
URL = (
    "https://globaldigitalinclusion.org/wp-content/uploads/2024/10/"
    "GDIP-Data-Device-Pricing-2024-Public.csv"
)
CACHE = Path(__file__).resolve().parent / "cache" / "device_pricing_2024.json"
COUNTRY_REF = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "data" / "2027 individual indicators" / "gdip-smartphone-transposed.csv"

PRICE = "Cheapest smartphone price (USD)"
AFFORDABILITY = "Cheapest smartphone affordability (% of monthly GNI per capita)"
YEAR = "Data year"
ROWS = [PRICE, AFFORDABILITY, YEAR]


def side_countries() -> list[str]:
    with COUNTRY_REF.open(newline="", encoding="utf-8") as fh:
        return [
            row[0]
            for row in list(csv.reader(fh))[1:]
            if row and row[0] and row[0] != "Coefficient of variation"
        ]


def fetch(use_cache: bool = True) -> dict[str, dict]:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        text = resp.read().decode("utf-8-sig", "ignore")

    data: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("DeviceType") != "Smart":
            continue
        iso = row.get("IsoCode")
        if not iso:
            continue
        try:
            price = float(row["CostUSD"])
        except (KeyError, TypeError, ValueError):
            continue
        try:
            affordability = float(row["Affordability"]) * 100
        except (KeyError, TypeError, ValueError):
            affordability = None

        current = data.get(iso)
        if current is None or price < current["price_usd"]:
            data[iso] = {
                "price_usd": price,
                "affordability_pct": affordability,
                "year": 2024,
                "brand": row.get("Brand") or "",
                "model": row.get("Type") or "",
            }

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return data


def fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def main() -> int:
    data = fetch(use_cache=True)
    countries = side_countries()

    columns = {row: [] for row in ROWS}
    for country in countries:
        iso = ISO3.get(country)
        record = data.get(iso) if iso else None
        columns[PRICE].append(fmt(record["price_usd"] if record else None))
        columns[AFFORDABILITY].append(
            fmt(record["affordability_pct"] if record else None)
        )
        columns[YEAR].append(str(record["year"]) if record else "-")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Indicator"] + countries)
        for row in ROWS:
            writer.writerow([row] + columns[row])

    missing = [c for c, value in zip(countries, columns[PRICE]) if value == "-"]
    print(
        f"Wrote {OUT} ({len(countries)} countries, "
        f"{len(countries) - len(missing)} priced, missing: {', '.join(missing) or 'none'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
