#!/usr/bin/env python3
"""Fetch the Tortoise / Observer Global AI Index infrastructure scores.

Source: https://observer.co.uk/data/global-ai

The rankings table on that page is a Flourish embed. We locate the embed from
``section#table`` (rather than hard-coding the visualisation ID), fetch it, and
read each country row's ``data-score-infra`` attribute.

The published scores are rounded integers. The European Union aggregate is
excluded because it is not a country.

Run:  python scripts/data_sources/tortoise/fetch_tortoise_ai.py
"""
from __future__ import annotations

import gzip
import json
import re
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

OBSERVER_URL = "https://observer.co.uk/data/global-ai"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    )
}
CACHE_DIR = Path(__file__).resolve().parent / "cache"
PAGE_CACHE = CACHE_DIR / "observer-global-ai.html"
EMBED_CACHE = CACHE_DIR / "flourish-embed.html"
DATA_CACHE = CACHE_DIR / "ai_infrastructure_2025.json"


def _get(url: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    return body.decode("utf-8", "ignore")


def _flourish_url(page: str) -> str:
    match = re.search(r"visualisation/(\d+)", page)
    if not match:
        raise RuntimeError("Could not find a Flourish visualisation on the Observer page")
    return f"https://flo.uri.sh/visualisation/{match.group(1)}/embed"


def _parse_scores(embed: str) -> dict[str, int]:
    soup = BeautifulSoup(embed, "html.parser")
    scores: dict[str, int] = {}
    for row in soup.select("div.row"):
        country = row.get("data-country")
        score = row.get("data-score-infra")
        if not country or country == "European Union" or score in (None, ""):
            continue
        scores[country] = int(round(float(score)))
    return scores


def fetch(use_cache: bool = True) -> dict:
    if use_cache and DATA_CACHE.exists():
        return json.loads(DATA_CACHE.read_text(encoding="utf-8"))

    if use_cache and PAGE_CACHE.exists():
        page = PAGE_CACHE.read_text(encoding="utf-8")
    else:
        page = _get(OBSERVER_URL)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        PAGE_CACHE.write_text(page, encoding="utf-8")

    url = _flourish_url(page)
    if use_cache and EMBED_CACHE.exists():
        embed = EMBED_CACHE.read_text(encoding="utf-8")
    else:
        embed = _get(url)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        EMBED_CACHE.write_text(embed, encoding="utf-8")

    scores = _parse_scores(embed)
    result = {
        "source": OBSERVER_URL,
        "embed": url,
        "edition": "2025",
        "indicator": "AI Infrastructure Score",
        "scores": scores,
    }
    DATA_CACHE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def main() -> int:
    data = fetch(use_cache=False)
    print(f"Cached {DATA_CACHE} ({len(data['scores'])} countries, {data['edition']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
