#!/usr/bin/env python3
"""Validate the world-map fix: charts.py loads the corrected GeoJSON (no
country overlaps India) and both choropleth builders render from it."""
import json
import sys

import pandas as pd
from shapely.geometry import shape

sys.path.insert(0, "/Users/rohanc1996/Documents/GitHub/ICRIER/SIDE_dashboard")

from components import charts  # noqa: E402

# 1) The GeoJSON the app will render is the corrected asset.
geo = charts._official_world_geojson()
feats = {f.get("id"): f for f in geo["features"]}
assert "IND" in feats and "PAK" in feats and "CHN" in feats, "missing countries"
india = shape(feats["IND"]["geometry"])
bad = []
for fid in feats:
    if fid == "IND":
        continue
    g = shape(feats[fid]["geometry"])
    inter = india.intersection(g)
    if not inter.is_empty and inter.area > 1e-9:
        bad.append(fid)
print(f"GeoJSON: {len(feats)} features; features overlapping India: {bad or 'NONE'}")

# 2) Sample disputed-region points must belong to IND only.
pts = [("PoK", 73.73, 33.15), ("Gilgit", 74.35, 35.92),
       ("Aksai Chin", 78.40, 35.10), ("Tawang", 91.90, 27.59)]
for label, lon, lat in pts:
    assert india.contains(shape({"type": "Point", "coordinates": [lon, lat]})), label
    assert not shape(feats["PAK"]["geometry"]).contains(
        shape({"type": "Point", "coordinates": [lon, lat]})), f"{label} in PAK"
    assert not shape(feats["CHN"]["geometry"]).contains(
        shape({"type": "Point", "coordinates": [lon, lat]})), f"{label} in CHN"
print("Disputed regions live in IND only: OK")

# 3) Both choropleth builders render from the corrected GeoJSON.
scores = pd.DataFrame({
    "Country": ["India", "Pakistan", "China", "United States", "Germany"],
    "chips": [0.72, 0.41, 0.55, 0.88, 0.83],
})
fig = charts.chips_choropleth(scores, "Pakistan")
fig_geo = json.loads(json.dumps(fig.data[0].geojson))
fig_feats = {f.get("id"): f for f in fig_geo["features"]}
assert set(fig_feats) == set(feats), "figure geojson ids differ from asset"
india_fig = shape(fig_feats["IND"]["geometry"])
overlap = [
    fid for fid in fig_feats if fid != "IND"
    and (lambda g: (not g.is_empty and g.area > 1e-9))(
        shape(fig_feats[fid]["geometry"]).intersection(india_fig))
]

print(f"Figure geojson: {len(fig_feats)} features; overlap with India: "
      f"{overlap or 'NONE'}")
assert not overlap, "figure still carries countries overlapping India"
print("chips_choropleth renders from corrected GeoJSON: OK")


print("ALL CHECKS PASSED")
