#!/usr/bin/env python3
"""Fetch Global Findex internet-use rates for the SIDE 2027 Connect pillar.

Source: World Bank API, Global Findex database (source 28).
Indicator: ``internet`` -- respondents who used the internet in the past three
months (% age 15+). The latest Findex wave (2025) reports 2024 data.

Qatar, Rwanda and the United Arab Emirates are not surveyed in this wave, so
they are absent from the result rather than stored as null.

Run:  python scripts/data_sources/world_bank/fetch_findex.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))

from fetch_undes import ISO3  # noqa: E402

INDICATOR = "internet"
YEAR = "2024"
SOURCE = "Global Findex Database (World Bank)"
LABEL = "Used the internet in the past three months (% age 15+)"
CACHE = Path(__file__).resolve().parent / "cache" / "findex_internet_2024.json"
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
