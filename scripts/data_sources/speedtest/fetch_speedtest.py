#!/usr/bin/env python3
"""Fetch the Speedtest Global Index country rankings.

Source: https://www.speedtest.net/global-index

The page ships both *mean* and *median* tables. SIDE uses median download
speeds, so only the ``medianSummary`` country tables are parsed. Mobile and
fixed broadband are separate tables; the page's city rankings are ignored.

Requests without a browser ``User-Agent`` are rejected with HTTP 403, so a
desktop Chrome UA is sent explicitly. Raw HTML and a normalized JSON snapshot
are cached next to this file so the CSV build reproduces without network
access.

Run:  python scripts/data_sources/speedtest/fetch_speedtest.py
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

URL = "https://www.speedtest.net/global-index"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
CACHE_DIR = Path(__file__).resolve().parent / "cache"
HTML_CACHE = CACHE_DIR / "global-index.html"
JSON_CACHE = CACHE_DIR / "global-index.json"

# Column container -> key in the normalized JSON.
TABLES = {
    "mobileMedian-results": "mobile",
    "fixedMedian-results": "fixed",
}


def _get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "ignore")


def _parse_country_table(soup: BeautifulSoup, column_class: str) -> dict[str, float]:
    """Return ``{country: median_mbps}`` for one median country table."""
    results: dict[str, float] = {}
    for column in soup.select(f".medianSummary .{column_class}"):
        for table in column.select(".countriesSummary table"):
            for row in table.find_all("tr"):
                cells = [
                    c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])
                ]
                if len(cells) < 4 or not cells[0].isdigit():
                    continue
                country = cells[2]
                try:
                    results[country] = float(cells[3])
                except ValueError:
                    continue
    return results


def _parse_month(soup: BeautifulSoup) -> str:
    month = soup.select_one(".page-header .month")
    return re.sub(r"\s+", " ", month.get_text(" ", strip=True)) if month else ""


def fetch(use_cache: bool = True) -> dict:
    """Fetch (or load cached) Speedtest median country speeds."""
    if use_cache and JSON_CACHE.exists():
        return json.loads(JSON_CACHE.read_text(encoding="utf-8"))

    if use_cache and HTML_CACHE.exists():
        html = HTML_CACHE.read_text(encoding="utf-8")
    else:
        html = _get(URL)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        HTML_CACHE.write_text(html, encoding="utf-8")

    soup = BeautifulSoup(html, "html.parser")
    data = {"source": URL, "month_label": _parse_month(soup)}
    for column_class, key in TABLES.items():
        data[key] = _parse_country_table(soup, column_class)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    JSON_CACHE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return data


def main() -> int:
    data = fetch(use_cache=False)
    print(
        f"Cached {JSON_CACHE} "
        f"({len(data['mobile'])} mobile, {len(data['fixed'])} fixed countries, "
        f"{data['month_label']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
