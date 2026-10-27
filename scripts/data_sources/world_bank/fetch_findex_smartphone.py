#!/usr/bin/env python3
"""Fetch Global Findex smartphone-use rates for the SIDE 2027 Connect pillar.

Source: World Bank API, Global Findex database (source 28).
Indicators (2024 wave):
    con5a -- phone used was a smartphone (% age 15+)
    con9a -- main mobile phone is a smartphone (% age 15+)

``con5a`` is only published for countries where the shared-phone question was
asked; it is absent for most high-income countries. ``con9a`` is available for
all but Qatar, Rwanda and the UAE.

Run:  python scripts/data_sources/world_bank/fetch_findex_smartphone.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "itu"))

from fetch_undes import ISO3  # noqa: E402

YEAR = "2024"
SOURCE = "Global Findex Database (World Bank)"
INDICATORS = {
    "con5a": "Phone used was a smartphone (% age 15+)",
    "con9a": "Main mobile phone is a smartphone (% age 15+)",
}
CACHE = Path(__file__).resolve().parent / "cache" / "findex_smartphone_2024.json"
BASE = "https://api.worldbank.org/v2"


def _fetch_indicator(code: str) -> dict[str, float]:
    countries = ";".join(ISO3.values())
    url = (
        f"{BASE}/country/{countries}/indicator/{code}"
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
        if iso in ISO3.values():
            values[iso] = float(row["value"])
    return values


def fetch(use_cache: bool = True) -> dict:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    result = {
        "source": SOURCE,
        "year": YEAR,
        "indicators": INDICATORS,
        "values": {code: _fetch_indicator(code) for code in INDICATORS},
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def main() -> int:
    data = fetch(use_cache=False)
    for code, label in INDICATORS.items():
        missing = sorted(set(ISO3.values()) - set(data["values"][code]))
        print(
            f"{code}: {label} -- {len(data['values'][code])} of {len(ISO3)} "
            f"countries; missing: {', '.join(missing) or 'none'}"
        )
    print(f"Cached {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
