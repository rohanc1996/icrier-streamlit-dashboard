"""Place data-centre facilities inside Aqueduct 4.0 sub-basins.

Both facility layers are point datasets; Aqueduct supplies polygons covering
the intersection of hydrological sub-basins, provinces and aquifers.  Each point
is joined to the polygon that contains it and inherits that polygon's water-risk
attributes.

Verification is part of the script, not an afterthought.  A random sample of
points is re-tested with a pure-Python ray-casting containment check that shares
no code with the geopandas spatial index, so a change in projection handling or
an index regression fails loudly rather than silently shifting basins.

Usage
-----
    ./.venv/bin/python scripts/data_sources/datacenters/spatial_join.py

Reads
-----
    data/derived/water_stress/raw/aqueduct/aqueduct40_baseline_annual.gpkg
    data/derived/water_stress/raw/peeringdb/peeringdb_facilities_*.csv
    data/derived/water_stress/raw/epoch/epoch_sites.csv

Writes
------
    data/derived/water_stress/facilities_joined.csv
"""

from __future__ import annotations

import argparse
import glob
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ATTRS = [
    "aq30_id",
    "pfaf_id",
    "gid_0",
    "name_0",
    "name_1",
    "area_km2",
    "bws_raw",
    "bws_score",
    "bws_cat",
    "bws_label",
    "drr_cat",
    "gtd_raw",
    "gtd_cat",
]


def ray_cast_contains(polygon, x: float, y: float) -> bool:
    """Independent containment test used only for verification."""
    parts = polygon.geoms if polygon.geom_type == "MultiPolygon" else [polygon]
    for part in parts:
        if not part.contains(Point(x, y)) and not _ring_contains(part, x, y):
            continue
        return True
    return False


def _ring_contains(part, x: float, y: float) -> bool:
    """Ray casting on the exterior ring, holes checked separately."""
    coords = list(part.exterior.coords)
    inside = False
    j = len(coords) - 1
    for i in range(len(coords)):
        xi, yi = coords[i]
        xj, yj = coords[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    if not inside:
        return False
    for hole in part.interiors:
        hx = list(hole.coords)
        hit = False
        j = len(hx) - 1
        for i in range(len(hx)):
            xi, yi = hx[i]
            xj, yj = hx[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                hit = not hit
            j = i
        if hit:
            return False
    return True


def load_points(raw: Path) -> pd.DataFrame:
    """Combine PeeringDB and Epoch into one point table."""
    pdb_files = sorted(glob.glob(str(raw / "peeringdb" / "peeringdb_facilities_*.csv")))
    if not pdb_files:
        raise FileNotFoundError("no PeeringDB snapshot; run fetch_peeringdb.py first")
    peeringdb = pd.read_csv(pdb_files[-1])
    peeringdb = peeringdb.rename(columns={"id": "source_id", "name": "name"})
    peeringdb["source"] = "peeringdb"
    peeringdb["mw"] = pd.NA
    peeringdb["net_count"] = pd.to_numeric(peeringdb["net_count"], errors="coerce")

    epoch = pd.read_csv(raw / "epoch" / "epoch_sites.csv")
    epoch = epoch.rename(columns={
        "Name": "name",
        "Current power (MW)": "mw",
        "geocode_source": "geocode_source",
    })
    epoch["source"] = "epoch"
    epoch["source_id"] = range(1, len(epoch) + 1)
    epoch["country"] = epoch["Country"]
    epoch["net_count"] = pd.NA

    columns = ["source", "source_id", "name", "country", "city", "state",
               "latitude", "longitude", "lat", "lon", "mw", "net_count",
               "geocode_source"]
    frame = pd.concat(
        [peeringdb.reindex(columns=columns), epoch.reindex(columns=columns)],
        ignore_index=True,
    )
    frame["lat"] = frame["lat"].fillna(frame["latitude"])
    frame["lon"] = frame["lon"].fillna(frame["longitude"])
    return frame.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/derived/water_stress/raw"))
    parser.add_argument("--out", type=Path,
                        default=Path("data/derived/water_stress/facilities_joined.csv"))
    parser.add_argument("--sample", type=int, default=25)
    args = parser.parse_args()

    basins = gpd.read_file(args.raw / "aqueduct" / "aqueduct40_baseline_annual.gpkg",
                           layer="baseline_annual")
    keep = [column for column in ATTRS if column in basins.columns]
    print(f"  {len(basins):,} basins, columns {len(keep)}")

    points = load_points(args.raw)
    print(f"  {len(points):,} facilities with coordinates "
          f"({(points.source == 'peeringdb').sum():,} PeeringDB, "
          f"{(points.source == 'epoch').sum():,} Epoch)")

    joined = gpd.sjoin(
        gpd.GeoDataFrame(points, geometry=gpd.points_from_xy(points.lon, points.lat),
                         crs="EPSG:4326"),
        basins[keep + ["geometry"]],
        how="left",
        predicate="within",
    )

    # A point sitting exactly on a shared boundary can match more than once.
    # Keep the smallest unit: it is the most specific description of the site.
    joined = (joined.sort_values("area_km2")
                    .drop_duplicates(subset=["source", "source_id"], keep="first"))

    matched = joined["gid_0"].notna()
    print(f"  matched {matched.sum():,}/{len(joined):,} "
          f"({matched.mean() * 100:.1f}%) to a sub-basin")

    # --- independent verification -------------------------------------------------
    sample = joined[matched].sample(min(args.sample, matched.sum()), random_state=7)
    basins_by_id = basins.set_index("aq30_id")
    failures = 0
    for _, row in sample.iterrows():
        polygon = basins_by_id.loc[row["aq30_id"], "geometry"]
        if not ray_cast_contains(polygon, row["lon"], row["lat"]):
            failures += 1
            print(f"    MISMATCH {row['source']} {row['name']}: "
                  f"{row['lon']:.4f},{row['lat']:.4f} not in aq30_id {row['aq30_id']}")
    print(f"  verification: {len(sample) - failures}/{len(sample)} agree with "
          f"independent ray casting")
    if failures:
        print("  refusing to write output while verification fails")
        return 1

    unmatched = joined[~matched]
    if len(unmatched):
        print(f"  unmatched by source: "
              f"{unmatched['source'].value_counts().to_dict()}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    columns = (["source", "source_id", "name", "country", "city", "lat", "lon",
                "mw", "net_count", "geocode_source"] + keep)
    joined[columns].to_csv(args.out, index=False)
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
