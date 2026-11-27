"""Download the PeeringDB facility snapshot used by the 2027 water-stress indicator.

PeeringDB is a crowd-maintained interconnection database.  Its AUP permits use
for research and analysis but forbids bulk redistribution, so the snapshot this
script writes is *never* committed; only country-level aggregates derived from
it enter the repository.  See `docs/decisions/0006-datacenter-water-stress.md`.

The API is rate limited.  A full sweep of ~5,900 facilities takes several
minutes at one page per three seconds, so the default settings are deliberately
conservative: 250 records per page (the API maximum), three seconds between
calls, and exponential backoff on HTTP 429.

Usage
-----
    ./.venv/bin/python scripts/data_sources/datacenters/fetch_peeringdb.py

Writes
------
    data/derived/water_stress/raw/peeringdb/peeringdb_facilities_<date>.json
    data/derived/water_stress/raw/peeringdb/peeringdb_facilities_<date>.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

API = "https://www.peeringdb.com/api/fac"
USER_AGENT = "SIDE-2027-research/0.1 (ICRIER; water-stress indicator)"
KEEP = [
    "id",
    "name",
    "aka",
    "city",
    "state",
    "country",
    "latitude",
    "longitude",
    "net_count",
    "ix_count",
    "carrier_count",
    "org_name",
    "campus_id",
    "updated",
]


def fetch_page(skip: int, limit: int, sleep: float, retries: int = 6) -> list[dict]:
    """Return one page of facility records, with backoff on rate limiting."""
    url = f"{API}?limit={limit}&skip={skip}"
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = json.load(response)
            return payload.get("data", [])
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            wait = sleep * (attempt + 1) * 3
            print(f"  retry {attempt + 1}/{retries} at skip={skip}: {error}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"giving up at skip={skip} after {retries} retries")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("data/derived/water_stress/raw/peeringdb"))
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--sleep", type=float, default=3.0)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()

    rows: list[dict] = []
    skip = 0
    while True:
        page = fetch_page(skip, args.limit, args.sleep)
        rows.extend(page)
        print(f"  {skip + len(page):>5} facilities", flush=True)
        if len(page) < args.limit:
            break
        skip += args.limit
        time.sleep(args.sleep)

    if not rows:
        print("no records returned; aborting", file=sys.stderr)
        return 1

    json_path = args.out / f"peeringdb_facilities_{stamp}.json"
    with json_path.open("w") as handle:
        json.dump(rows, handle)

    frame = pd.DataFrame(rows)
    frame = frame[[column for column in KEEP if column in frame.columns]]
    csv_path = args.out / f"peeringdb_facilities_{stamp}.csv"
    frame.to_csv(csv_path, index=False)

    with_coords = frame[["latitude", "longitude"]].notna().all(axis=1).sum()
    print(f"wrote {len(frame)} facilities ({with_coords} with coordinates)")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
