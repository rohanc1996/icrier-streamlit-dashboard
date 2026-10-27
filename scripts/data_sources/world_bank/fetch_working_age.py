#!/usr/bin/env python3
"""Fetch World Bank working-age population for the SIDE 2027 AI-users pillar.

Source: World Bank WDI, indicator ``SP.POP.1564.TO`` (Population ages 15-64,
total). The latest year available for the 71 SIDE countries is 2025.

Run:  python scripts/data_sources/world_bank/fetch_working_age.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))

from fetch_undes import ISO3  # noqa: E402

INDICATOR = "SP.POP.1564.TO"
YEAR = "2025"
SOURCE = "World Development Indicators (World Bank)"
LABEL = "Population ages 15-64, total"
CACHE = Path(__file__).resolve().parent / "cache" / "working_age_population_2025.json"
BASE = "https://api.worldbank.org/v2"


def fetch(use_cache: bool = True) -> dict:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    countries = ";".join(ISO3.values())
    url = (
        f"{BASE}/country/{countries}/indicator/{INDICATOR}"
        f"?format=json&per_page=2000&date={YEAR}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    values: dict[str, float] = {}
    for row in payload[1] or []:
        if row.get("value") is None:
            continue
        iso = row.get("countryiso3code") or (row.get("country") or {}).get("id")
        if iso and iso in ISO3.values():
            values[iso] = float(row["value"])

    result = {
        "source": SOURCE,
        "indicator": LABEL,
        "api_indicator": INDICATOR,
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
    missing = sorted(set(ISO3.values()) - set(data["values"]))
    print(
        f"Cached {CACHE} ({len(data['values'])} of {len(ISO3)} countries, "
        f"{data['year']}); missing: {', '.join(missing) or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
