#!/usr/bin/env python3
"""Build ``data/SIDE 2027 - Speedtest data.csv`` from the Speedtest cache.

The output mirrors the SIDE absolute CSV shape: one ``Country`` column plus the
two canonical median-speed headers, one row per SIDE country in the same order,
values to two decimals and ``-`` for missing data. A trailing
``Coefficient of variation`` row is computed with the same population standard
deviation used elsewhere in the repo.

Source cache: ``scripts/data_sources/speedtest/cache/global-index.json``
(fetched by ``fetch_speedtest.py``).

Run:  python scripts/data_sources/speedtest/build_speedtest_csv.py
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_speedtest import fetch  # noqa: E402

COUNTRY_REF = ROOT / "data" / "SIDE 2027 - Absolute.csv"
OUT = ROOT / "data" / "SIDE 2027 - Speedtest data.csv"

MOBILE_HEADER = "Median Mobile Download Speeds (Mbps)"
FIXED_HEADER = "Median Fixed Broadband Download Speed (Mbps)"

# Speedtest country name -> SIDE country name.
ALIASES = {
    "South Korea": "Republic of Korea",
    "United States": "United States of America",
    "Vietnam": "Viet Nam",
}


def side_countries() -> list[str]:
    with COUNTRY_REF.open(newline="", encoding="utf-8") as fh:
        return [
            row[0]
            for row in list(csv.reader(fh))[1:]
            if row and row[0] and row[0] != "Coefficient of variation"
        ]


def _remap(values: dict[str, float]) -> dict[str, float]:
    out = dict(values)
    for source, target in ALIASES.items():
        if source in values:
            out[target] = values[source]
    return out


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def _cv(values: list[float]) -> str:
    if not values:
        return "-"
    return f"{statistics.pstdev(values) / statistics.mean(values):.2f}"


def main() -> int:
    data = fetch(use_cache=True)
    mobile = _remap(data["mobile"])
    fixed = _remap(data["fixed"])
    countries = side_countries()

    mobile_values: list[float] = []
    fixed_values: list[float] = []
    rows: list[list[str]] = []
    missing: list[str] = []

    for country in countries:
        m = mobile.get(country)
        f = fixed.get(country)
        if m is not None:
            mobile_values.append(m)
        if f is not None:
            fixed_values.append(f)
        if m is None or f is None:
            missing.append(country)
        rows.append([country, _fmt(m), _fmt(f)])

    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Country", MOBILE_HEADER, FIXED_HEADER])
        writer.writerows(rows)
        writer.writerow([])
        writer.writerow(
            ["Coefficient of variation", _cv(mobile_values), _cv(fixed_values)]
        )
        writer.writerow([])

    print(
        f"Wrote {OUT} ({len(rows)} countries, {data['month_label']}, "
        f"missing: {', '.join(missing) or 'none'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
