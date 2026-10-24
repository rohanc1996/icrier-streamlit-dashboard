#!/usr/bin/env python3
"""Fetch the Q2 2026 Microsoft AI Diffusion country data.

Source: https://github.com/microsoft/ai-diffusion-report
        data/AI_Diffusion_Q22026_Update.csv
        (report: https://aka.ms/AIDiffusionReport2026Q2)

The CSV reports AI user share by economy. Q2 2026 is the last column. The file
is not clean UTF-8 (one country label contains a stray 0x9F byte), so it is
decoded as latin-1.

Run:  python scripts/data_sources/microsoft_ai_diffusion/fetch_ai_diffusion.py
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from pathlib import Path

URL = (
    "https://raw.githubusercontent.com/microsoft/ai-diffusion-report/main/"
    "data/AI_Diffusion_Q22026_Update.csv"
)
SOURCE = "https://github.com/microsoft/ai-diffusion-report"
PERIOD = "Q2 2026"
CACHE = Path(__file__).resolve().parent / "cache" / "ai_diffusion_q2_2026.json"


def fetch(use_cache: bool = True) -> dict:
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))

    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        text = resp.read().decode("latin-1")

    shares: dict[str, float] = {}
    for row in csv.reader(io.StringIO(text)):
        if not row or len(row) < 5:
            continue
        country = row[0].strip()
        if not country or country.lower() == "economy":
            continue
        try:
            shares[country] = float(row[4].strip().rstrip("%"))
        except ValueError:
            continue

    result = {
        "source": SOURCE,
        "period": PERIOD,
        "indicator": "AI user share (% of working-age population)",
        "shares": shares,
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def main() -> int:
    data = fetch(use_cache=False)
    print(f"Cached {CACHE} ({len(data['shares'])} economies, {data['period']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
