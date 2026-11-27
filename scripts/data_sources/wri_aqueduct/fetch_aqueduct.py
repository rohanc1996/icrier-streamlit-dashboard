"""Fetch WRI Aqueduct 4.0 baseline water-risk geodata.

Aqueduct 4.0 (data vintage April 2023) is licensed CC BY 4.0.  The published
download is a 250 MB archive containing the baseline, monthly and future-
projection tables as CSV plus a FileGDB of the geometries.  The geometries are
the union of hydrological sub-basins, GADM provinces and WHYMAP aquifers, which
is why each unit already carries an ISO-3 country code (`gid_0`).

This script keeps only the baseline annual layer, prunes it to the columns the
indicator uses, and writes a GeoPackage that later steps load quickly.

Usage
-----
    ./.venv/bin/python scripts/data_sources/wri_aqueduct/fetch_aqueduct.py

Writes
------
    data/derived/water_stress/raw/aqueduct/aqueduct-4-0-water-risk-data.zip
    data/derived/water_stress/raw/aqueduct/aqueduct40_baseline_annual.gpkg
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

URL = "https://files.wri.org/aqueduct/aqueduct-4-0-water-risk-data.zip"
ARCHIVE = "aqueduct-4-0-water-risk-data.zip"
# Path inside the archive (year-stamped folder name).
GDB_MEMBER = "GDB/Aq40_Y2023D07M05.gdb"
BASELINE_CSV = "CVS/Aqueduct40_baseline_annual_y2023m07d05.csv"

COLUMNS = [
    "aq30_id",
    "pfaf_id",
    "gid_0",
    "gid_1",
    "name_0",
    "name_1",
    "aqid",
    "area_km2",
    "bws_raw",
    "bws_score",
    "bws_cat",
    "bws_label",
    "drr_raw",
    "drr_cat",
    "gtd_raw",
    "gtd_cat",
]


def download(target: Path) -> Path:
    """Download the archive once and reuse it thereafter."""
    if target.exists() and target.stat().st_size > 200_000_000:
        print(f"  using cached {target} ({target.stat().st_size / 1e6:.0f} MB)")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {URL}")
    with urllib.request.urlopen(URL, timeout=600) as response, target.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    print(f"  saved {target.stat().st_size / 1e6:.0f} MB")
    return target


def extract_baseline(archive: Path, workdir: Path) -> Path:
    """Pull the baseline FileGDB out of the archive."""
    gdb = workdir / "aqueduct40.gdb"
    if gdb.exists():
        return gdb
    workdir.mkdir(parents=True, exist_ok=True)
    marker = GDB_MEMBER.rsplit("/", 1)[-1] + "/"
    with zipfile.ZipFile(archive) as zf:
        members = [name for name in zf.namelist() if marker in name]
        if not members:
            raise FileNotFoundError(f"{GDB_MEMBER} not found inside {archive.name}")
        for name in members:
            suffix = name.split(marker, 1)[1]
            if not suffix:
                continue
            destination = gdb / suffix
            if name.endswith("/"):
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, destination.open("wb") as dst:
                dst.write(src.read())
    return gdb


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("data/derived/water_stress/raw/aqueduct"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    archive = download(args.out / ARCHIVE)
    gdb = extract_baseline(archive, args.out)

    print("  reading baseline_annual")
    frame = gpd.read_file(gdb, layer="baseline_annual")
    print(f"  {len(frame):,} polygons, crs={frame.crs}")

    keep = [column for column in COLUMNS if column in frame.columns]
    frame = frame[keep + ["geometry"]].to_crs("EPSG:4326")

    countries = frame["gid_0"].nunique()
    print(f"  {countries} countries/territories, "
          f"{frame['bws_raw'].notna().sum():,} with baseline water stress")

    target = args.out / "aqueduct40_baseline_annual.gpkg"
    frame.to_file(target, layer="baseline_annual", driver="GPKG")
    print(f"  wrote {target} ({target.stat().st_size / 1e6:.0f} MB)")

    # A compact attribute table is useful for auditing without loading geometry.
    frame.drop(columns="geometry").to_csv(
        args.out / "aqueduct40_baseline_annual_attributes.csv", index=False
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
