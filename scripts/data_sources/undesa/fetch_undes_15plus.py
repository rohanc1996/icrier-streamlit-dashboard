#!/usr/bin/env python3
"""Fetch UN DESA WPP 2024 population aged 15+ for the SIDE 2027 indicators.

Source: UN DESA World Population Prospects 2024, medium variant, both sexes,
served as a compact CSV by Our World in Data (the UN bulk file is extremely
slow to download). Population aged 15+ is total population minus the under-15
population; the total and under-15 series match the WPP 2024 projections.

Run:  python scripts/data_sources/undesa/fetch_undes_15plus.py
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))

from fetch_undes import ISO3  # noqa: E402

URL = "https://ourworldindata.org/grapher/population-by-age-group-with-projections.csv"
YEAR = "2026"
SOURCE = "UN DESA World Population Prospects 2024 (via Our World in Data)"
CACHE = Path(__file__).resolve().parent / "cache" / "undes_population_15plus_2026.json"
ISO_CODES = set(ISO3.values())


def fetch(use_cache: bool = True) -> dict:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        text = resp.read().decode("utf-8")

    values: dict[str, float] = {}
    for row in csv.DictReader(io.StringIO(text)):
        iso = row.get("Code")
        if iso not in ISO_CODES or row.get("Year") != YEAR:
            continue
        try:
            total = float(row["Total (Projected)"])
            under_15 = float(row["Under-15s (Projected)"])
        except (KeyError, TypeError, ValueError):
            continue
        if total > 0:
            values[iso] = total - under_15

    result = {
        "source": SOURCE,
        "indicator": "Population aged 15+",
        "year": YEAR,
        "values": values,
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def main() -> int:
    data = fetch(use_cache=False)
    missing = sorted(ISO_CODES - set(data["values"]))
    print(
        f"Cached {CACHE} ({len(data['values'])} of {len(ISO3)} countries, "
        f"{data['year']}); missing: {', '.join(missing) or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
