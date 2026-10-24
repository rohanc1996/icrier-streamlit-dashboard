#!/usr/bin/env python3
"""Fetch the latest ITU DataHub indicators used in the SIDE 2027 Connect pillar.

Source: https://api.datahub.itu.int/v3 (the API behind beta.datahub.itu.int;
the older ``/v2`` route is blocked by the DataHub WAF).

Indicators:
    392   Mobile-cellular subscriptions per 100 inhabitants
    11624 Individuals using the Internet (% of total population)
    19306 Population covered by at least LTE/WiMAX (% of population)
    38969 Mobile data and voice basket, high consumption (PPP$)
    38966 Mobile data and voice basket, low consumption (PPP$)
    33332 Fixed-broadband Internet basket, 5GB (PPP$)

The latest non-empty year is kept per country for each indicator. The API is
undocumented and intermittently rate-limits anonymous clients with HTTP 403,
so requests are retried with backoff.

Run:  python scripts/data_sources/itu/fetch_itu.py
"""
from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.datahub.itu.int/v3"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Origin": "https://beta.datahub.itu.int",
    "Referer": "https://beta.datahub.itu.int/",
}
CACHE_DIR = Path(__file__).resolve().parent / "cache"
ITU_CACHE = CACHE_DIR / "itu.json"

INDICATORS = {
    392: "mobile_per_100",
    11624: "internet_pct",
    19306: "lte_pct",
    38969: "mobile_hc_ppp",
    38966: "mobile_lc_ppp",
    33332: "fixed_ppp",
}


def _get(path: str, attempts: int = 6, timeout: int = 90) -> object:
    url = f"{BASE}/{path}"
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                if body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)
                return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (403, 429, 500, 502, 503, 504):
                raise
            time.sleep(3 * attempt)
    raise RuntimeError(f"ITU request failed after {attempts} attempts: {url}") from last_error


def _latest(records: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in records:
        answers = row.get("answer") or []
        if not answers or answers[0].get("value") in (None, ""):
            continue
        try:
            value = float(answers[0]["value"])
            year = int(row["dataYear"])
        except (KeyError, TypeError, ValueError):
            continue
        iso = row.get("isoCode")
        if not iso:
            continue
        if iso not in latest or year > latest[iso]["year"]:
            latest[iso] = {
                "value": value,
                "year": year,
                "note": row.get("dataNote") or "",
                "source": row.get("dataSource") or "",
            }
    return latest


def fetch(use_cache: bool = True) -> dict:
    if use_cache and ITU_CACHE.exists():
        return json.loads(ITU_CACHE.read_text(encoding="utf-8"))

    data: dict[str, dict] = {}
    for code_id, key in INDICATORS.items():
        data[key] = _latest(_get(f"data/bycode/{code_id}"))
        time.sleep(2)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ITU_CACHE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return data


def main() -> int:
    data = fetch(use_cache=False)
    print(
        f"Cached {ITU_CACHE} "
        f"({len(data['mobile_per_100'])} mobile, "
        f"{len(data['internet_pct'])} internet countries)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
