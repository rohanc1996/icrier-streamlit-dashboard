"""Fetch Epoch AI's frontier data-centre database and resolve site coordinates.

Epoch AI tracks the largest AI data centres from satellite imagery, permits and
company disclosures, publishing site power capacity in MW under CC BY 4.0.  The
public CSV carries the site name, country and street address, but no
coordinates, so this script geocodes them once and caches the result as a
reviewable fixture.

Geocoding order for each site:

1. a manual override in ``data/reference/epoch_sites_manual_geocodes.csv``
   (used where the address is missing, ambiguous, or resolves to a country
   centroid -- a centroid would place the campus in an arbitrary basin);
2. the street address, via Nominatim;
3. the city and country, via Nominatim;
4. otherwise the site is marked ``unresolved`` and dropped from the join.

Nominatim asks for one request per second; a cold run takes a few minutes.
The fixture is committed so routine runs never hit the network.

Usage
-----
    ./.venv/bin/python scripts/data_sources/datacenters/fetch_epoch.py

Writes
------
    data/derived/water_stress/raw/epoch/data_centers.csv
    data/derived/water_stress/raw/epoch/data_center_timelines.csv
    data/reference/epoch_sites_geocoded.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

BASE = "https://epoch.ai/data/data_centers"
USER_AGENT = "SIDE-2027-research/0.1 (ICRIER; water-stress indicator)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def fetch(url: str, target: Path, timeout: int = 120) -> Path:
    if target.exists():
        print(f"  using cached {target.name}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        target.write_bytes(response.read())
    print(f"  saved {target.name}")
    return target


def geocode(query: str) -> dict | None:
    """One Nominatim lookup.  Returns lat/lon plus the display name."""
    url = f"{NOMINATIM}?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    )
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                hits = json.load(response)
            if not hits:
                return None
            hit = hits[0]
            return {
                "lat": float(hit["lat"]),
                "lon": float(hit["lon"]),
                "display": hit.get("display_name", ""),
            }
        except Exception as error:  # noqa: BLE001 - network flakiness is expected
            print(f"    retry {attempt + 1}: {error}", file=sys.stderr)
            time.sleep(3 * (attempt + 1))
    return None


def resolve(row: pd.Series, overrides: dict[str, dict]) -> dict:
    """Coordinates for one site, following the documented order."""
    name = row["Name"]
    if name in overrides:
        entry = overrides[name]
        return {
            "lat": entry["lat"],
            "lon": entry["lon"],
            "geocode_source": entry["source"],
            "geocode_note": entry["note"],
            "geocode_display": "",
        }

    address = str(row.get("Address", "") or "").strip()
    country = str(row.get("Country", "") or "").strip()

    if address:
        hit = geocode(", ".join(part for part in (address, country) if part))
        time.sleep(1.1)
        if hit:
            return {
                "lat": hit["lat"],
                "lon": hit["lon"],
                "geocode_source": "address",
                "geocode_note": "",
                "geocode_display": hit["display"],
            }

    city = ""
    if "," in address:
        city = address.split(",")[-2].strip()
    if city:
        hit = geocode(", ".join(part for part in (city, country) if part))
        time.sleep(1.1)
        if hit:
            return {
                "lat": hit["lat"],
                "lon": hit["lon"],
                "geocode_source": "city",
                "geocode_note": "",
                "geocode_display": hit["display"],
            }

    return {"lat": None, "lon": None, "geocode_source": "unresolved",
            "geocode_note": "no address and no city match", "geocode_display": ""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path,
                        default=Path("data/derived/water_stress/raw/epoch"))
    parser.add_argument("--fixture", type=Path,
                        default=Path("data/reference/epoch_sites_geocoded.csv"))
    parser.add_argument("--overrides", type=Path,
                        default=Path("data/reference/epoch_sites_manual_geocodes.csv"))
    parser.add_argument("--regeocode", action="store_true",
                        help="ignore the cached fixture and geocode from scratch")
    args = parser.parse_args()

    fetch(f"{BASE}/data_centers.csv", args.raw / "data_centers.csv")
    fetch(f"{BASE}/data_center_timelines.csv", args.raw / "data_center_timelines.csv")

    sites = pd.read_csv(args.raw / "data_centers.csv", dtype=str, keep_default_na=False)
    print(f"  {len(sites)} sites, {sites['Current power (MW)'].ne('').sum()} with power")

    overrides: dict[str, dict] = {}
    if args.overrides.exists():
        manual = pd.read_csv(args.overrides, keep_default_na=False)
        for _, row in manual.iterrows():
            overrides[row["name"]] = {
                "lat": float(row["lat"]) if str(row["lat"]).strip() else None,
                "lon": float(row["lon"]) if str(row["lon"]).strip() else None,
                "source": row["source"],
                "note": row["note"],
            }

    if args.fixture.exists() and not args.regeocode:
        print(f"  using cached fixture {args.fixture}")
        frame = pd.read_csv(args.fixture, keep_default_na=False)
        known = set(frame["Name"])
        missing = [name for name in sites["Name"] if name not in known]
        if missing:
            print(f"  {len(missing)} new sites need geocoding")
            args.regeocode = True

    if args.regeocode or not args.fixture.exists():
        rows = []
        for _, row in sites.iterrows():
            resolved = resolve(row, overrides)
            rows.append({"Name": row["Name"], **resolved})
            print(f"  {row['Name'][:44]:<44} {resolved['geocode_source']}")
        frame = pd.DataFrame(rows)
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.fixture, index=False)
        print(f"  wrote {args.fixture}")

    merged = sites.merge(frame, on="Name", how="left")
    merged["Current power (MW)"] = pd.to_numeric(
        merged["Current power (MW)"], errors="coerce"
    )
    located = merged.dropna(subset=["lat", "lon"])
    print(f"  located {len(located)}/{len(merged)} sites, "
          f"{located['Current power (MW)'].sum():,.0f} MW of "
          f"{merged['Current power (MW)'].sum():,.0f} MW")

    output = args.raw / "epoch_sites.csv"
    merged.to_csv(output, index=False)
    print(f"  wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
