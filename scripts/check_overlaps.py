#!/usr/bin/env python3
"""Check whether any country feature overlaps India (IND) in the merged world
GeoJSON, and print the intersection areas."""
import json
import sys

from shapely.geometry import shape

GEO = "/Users/rohanc1996/Documents/GitHub/ICRIER/SIDE_dashboard/assets/world_india_official.geojson"


def main() -> int:
    d = json.load(open(GEO, encoding="utf-8"))
    feats = {f.get("id"): f for f in d["features"]}
    print("total features:", len(feats))

    india = shape(feats["IND"]["geometry"])
    print("IND type:", india.geom_type, "area:", india.area, "bbox:", india.bounds)

    overlaps = []
    for fid, feat in feats.items():
        if fid == "IND":
            continue
        g = shape(feat["geometry"])
        if not g.intersects(india):
            continue
        inter = india.intersection(g)
        if inter.is_empty:
            continue
        overlaps.append((fid, inter.area, 100 * inter.area / max(g.area, 1e-12)))

    overlaps.sort(key=lambda t: -t[1])
    if not overlaps:
        print("No overlaps with India found.")
        return 0
    print(f"{len(overlaps)} feature(s) overlap India:")
    for fid, area, pct in overlaps[:30]:
        print(f"  {fid}: intersection area={area:.6f} ({pct:.4f}% of that country)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
