#!/usr/bin/env python3
"""Fetch the OECD AI-compute tables behind the "GPU availability by country
and AI capability" visualization.

Source chain (all public, no API key):

1. WP REST lists the visualization and its chart id:
     https://wp.oecd.ai/wp-json/wp/v2/visualizations?search=gpu
     -> slug ``gpu-availability-by-country-and-ai-capability``, ``acf.chartId``.
2. The chart config points at the GraphQL backend:
     https://observatory.oecdai.org/api/v1/chart-cfg/<chartId>
     -> ``database: o2__compute``, ``graphqlApiUrl``.
3. GraphQL exposes the country-level tables used here:
     ``az_avail``  - availability zones by AI capability (counts and %)
     ``gpu_avail`` - GPU-level breakdown (one row per country x tier x GPU)

The OECD data come from original research by the OECD in collaboration with
Oxford University Innovation and must be attributed as such.

This module only *fetches* and caches; ``build_2027_oecd_compute.py`` turns the
cache into SIDE columns.  Raw responses are cached next to this file under
``cache/`` so the build reproduces without network access.

Run:  python scripts/data_sources/oecd/fetch_oecd_compute.py
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

GRAPHQL_URL = "https://observatory.oecdai.org/graphql/v1"
CACHE_DIR = Path(__file__).resolve().parent / "cache"
AZ_AVAIL_CACHE = CACHE_DIR / "o2__compute__az_avail.json"
GPU_AVAIL_CACHE = CACHE_DIR / "o2__compute__gpu_avail.json"

AZ_AVAIL_QUERY = """{
  o2__compute {
    az_avail {
      country
      unit
      Total_AZs
      az_has_training_gpu
      az_has_finetuning_gpu
      az_has_inferencing_gpu
      az_has_nonAI_gpu
      az_has_no_gpu
    }
  }
}"""

GPU_AVAIL_QUERY = """{
  o2__compute {
    gpu_avail {
      country
      Tier
      GPU
      value
    }
  }
}"""


def _graphql(query: str, timeout: int = 60) -> list[dict]:
    """POST a GraphQL query and return the flat list of rows for the table.

    The response shape is ``{"data": {"o2__compute": {"<table>": [...]}}}``;
    the single table key is inferred from the query.
    """
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if "errors" in body and body["errors"]:
        raise RuntimeError(f"GraphQL error: {body['errors']}")
    compute = body["data"]["o2__compute"]
    table = next(iter(compute))
    return compute[table]


def _load_or_fetch(cache: Path, query: str, use_cache: bool) -> list[dict]:
    if use_cache and cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    rows = _graphql(query)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def fetch_az_avail(use_cache: bool = True) -> list[dict]:
    """Availability zones by country and AI capability (counts and %)."""
    return _load_or_fetch(AZ_AVAIL_CACHE, AZ_AVAIL_QUERY, use_cache)


def fetch_gpu_avail(use_cache: bool = True) -> list[dict]:
    """GPU-level availability (country x tier x GPU -> number of AZs)."""
    return _load_or_fetch(GPU_AVAIL_CACHE, GPU_AVAIL_QUERY, use_cache)


def main() -> int:
    az = fetch_az_avail(use_cache=False)
    gpu = fetch_gpu_avail(use_cache=False)
    print(f"Cached {AZ_AVAIL_CACHE} ({len(az)} rows)")
    print(f"Cached {GPU_AVAIL_CACHE} ({len(gpu)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
