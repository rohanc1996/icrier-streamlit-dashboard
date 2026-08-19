#!/usr/bin/env python3
"""Build a world GeoJSON whose India geometry is the official Government of
India / Survey of India territorial extent.

Strategy
--------
Plotly's built-in ``locationmode="country names"`` / ``"ISO-3"`` choropleths
render Natural Earth boundaries, which show *de facto* borders (India cut at
the Line of Control, PoK/Gilgit-Baltistan and Aksai Chin as separate units,
dashed claims along Arunachal Pradesh).  Natural Earth never matches the
official Indian map, and Plotly has no switch for this.

The fix: build our own world GeoJSON where Natural Earth's de-facto India
(and the disputed fragments it absorbs) is *replaced* by the union of the 36
official state/Union-Territory polygons published in Survey-of-India-derived
open data.  The dashboard then renders that GeoJSON via ``geojson=`` +
``featureidkey="id"``, so India displays at its full official extent.
Neighbouring countries whose Natural Earth polygons extend into that official
extent (Pakistan's PoK/Gilgit-Baltistan, China's Aksai Chin, and small border
slivers with Bangladesh, Nepal, Bhutan, Myanmar and Afghanistan) are clipped
against it, so no other country's outline overlaps India.

Output
------
A FeatureCollection where every feature carries an ``id`` used for matching
(``featureidkey="id"``): its ISO-3 code where one exists, otherwise Natural
Earth's ``ADM0_A3`` admin code (e.g. Somaliland = ``SOL``) or a name-based
slug as a last resort.  The India feature has ``id = "IND"`` and its geometry
is the union (``shapely.ops.unary_union``) of all 36 state/UT polygons, which
dissolves the interior state boundaries into one national outline.

Usage (run once; runtime does not need shapely)
------------------------------------------------
    python scripts/build_official_world.py \\
        --world /path/to/ne_110m_admin_0_countries.geojson \\
        --india /path/to/india-states-simplified.geojson \\
        --out SIDE_dashboard/assets/world_india_official.geojson

Data sources
------------
* World: Natural Earth 1:110m admin-0 countries (sovereign states), e.g. from
  https://github.com/nvkelso/natural-earth-vector (``geojson/ne_110m_admin_0_countries.geojson``).
* India: ``india-states-simplified.geojson`` from
  https://github.com/AbhinavSwami28/india-official-geojson (MIT) - 36 official
  state/UT polygons built from Survey-of-India-derived data (J&K in full incl.
  PoK/Gilgit-Baltistan/Siachen, Ladakh incl. Aksai Chin, Arunachal Pradesh in
  full).  Cross-check against the latest Survey of India map before publishing.

Legal
-----
(c) Survey of India - reproduction of the map of India requires attribution.
Verify boundaries against the latest Survey of India publication.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

# Extra safety net: drop Natural Earth features by name even if the
# containment check below misses them (NE names vary across versions).
DROP_NAME_HINTS = (
    "kashmir", "gilgit", "aksai chin", "siachen",
    "china/india", "india/china",
)

# NE sometimes labels the de-facto India feature "India" under ADMIN/NAME.
INDIA_NAME_HINTS = ("india",)

def _feature_name(feat: dict) -> str:
    props = feat.get("properties", {}) or {}
    for key in ("NAME", "ADMIN", "name", "NAME_LONG", "NAME_EN"):
        if props.get(key):
            return str(props[key])
    return ""


def _feature_iso3(feat: dict) -> str | None:
    """Return a usable ISO-3 code for a Natural Earth feature, or None."""
    props = feat.get("properties", {}) or {}
    for key in ("ISO_A3", "ISO_A3_EH", "WB_A3"):
        code = props.get(key)
        if code and code not in ("-99", "-1", "null", "0"):
            return str(code)
    return None


def _geometry_to_dict(geom) -> dict:
    """Shapely geometry -> plain dict (via GeoJSON round-trip)."""
    return json.loads(json.dumps(geom.__geo_interface__))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True,
                        help="Natural Earth admin-0 countries GeoJSON")
    parser.add_argument("--india", required=True,
                        help="Official India states/UTs GeoJSON")
    parser.add_argument("--out", required=True,
                        help="Where to write the merged world GeoJSON")
    args = parser.parse_args()

    world = json.loads(Path(args.world).read_text(encoding="utf-8"))
    india_states = json.loads(Path(args.india).read_text(encoding="utf-8"))
    if world.get("type") != "FeatureCollection":
        sys.exit("--world must be a GeoJSON FeatureCollection")
    if india_states.get("type") != "FeatureCollection":
        sys.exit("--india must be a GeoJSON FeatureCollection")

    # 1) Official India geometry: union of all state/UT polygons.
    state_geoms = []
    for feat in india_states["features"]:
        geom = shape(feat["geometry"])
        if geom.is_empty:
            continue
        state_geoms.append(geom)
    if not state_geoms:
        sys.exit("--india contains no usable polygons")
    official_india = unary_union(state_geoms)
    print(f"Official India: {official_india.geom_type}, "
          f"bbox={official_india.bounds}", flush=True)



    kept = []
    dropped = []
    for feat in world["features"]:
        props = feat.get("properties", {}) or {}
        name = _feature_name(feat).lower()
        iso3 = _feature_iso3(feat)

        geom = shape(feat["geometry"])
        # Drop features that are essentially inside official India
        # (de-facto India, Kashmir, Azad Kashmir, Gilgit-Baltistan,
        # Aksai Chin, Siachen, China/India slivers...).
        inside = False
        if not geom.is_empty and not official_india.is_empty and geom.area:
            inside = geom.intersection(official_india).area >= 0.9 * geom.area
        drop = inside or any(h in name for h in DROP_NAME_HINTS) or (
            iso3 == "IND" or any(h in name for h in INDIA_NAME_HINTS)
        )
        if drop:
            dropped.append(name or iso3 or str(feat.get("id")))
            continue
        # Remove any part of this country that falls inside official India
        # (Pakistan's PoK/Gilgit-Baltistan, China's Aksai Chin, and small
        # boundary slivers with Bangladesh/Nepal/Bhutan/Myanmar/Afghanistan)
        # so no other country's polygon or outline overlaps India's extent.
        if geom.intersects(official_india):
            clipped_geom = geom.difference(official_india)
            if not clipped_geom.is_valid:
                clipped_geom = clipped_geom.buffer(0)
            if clipped_geom.is_empty:
                dropped.append(name or iso3 or str(feat.get("id")))
                continue
            feat = dict(feat)
            feat["geometry"] = _geometry_to_dict(clipped_geom)
        kept.append(feat)

    print(f"World features: {len(world['features'])} -> kept {len(kept)}, "
          f"dropped {len(dropped)}", flush=True)
    print("Dropped:", ", ".join(sorted(set(dropped))), flush=True)

    # 2) Append official India as a single feature.
    india_feature = {
        "type": "Feature",
        "id": "IND",
        "properties": {
            "name": "India",
            "ADMIN": "India",
            "ISO_A3": "IND",
            "ISO_A3_EH": "IND",
        },
        "geometry": _geometry_to_dict(official_india),
    }
    kept.append(india_feature)

    # 3) Normalise: every feature gets an ``id`` so the dashboard can use
    #    featureidkey="id" uniformly.  Real ISO-3 codes win; features without
    #    one (N. Cyprus, Somaliland, ...) fall back to Natural Earth's ADM0_A3
    #    admin code, then to a name slug — and the result is always made
    #    unique, so a fallback can never steal a real country's ISO-3 code.
    used_ids: set[str] = set()
    normalized = []
    for feat in kept:
        out = dict(feat)
        props = dict(feat.get("properties", {}) or {})
        iso3 = _feature_iso3(out) or props.get("id") or props.get("ISO3") \
            or str(out.get("id") or "")
        if not iso3 or iso3 in ("-99", "-1", "0"):
            # No usable ISO code (e.g. N. Cyprus, Somaliland): prefer Natural
            # Earth's ADM0_A3 admin code, then a name slug, so the id is never
            # empty and never collides with a real country's ISO-3.
            adm0 = str(props.get("ADM0_A3") or "")
            iso3 = adm0 if adm0 and adm0 not in ("-99", "-1", "0") else ""
            if not iso3:
                nm = _feature_name(out)
                iso3 = re.sub(r"[^A-Z0-9]+", "", nm.upper())[:3] if nm else "XXX"
        base, i = iso3, 1
        while iso3 in used_ids:
            i += 1
            iso3 = f"{base}{i}"
        used_ids.add(iso3)
        out["properties"] = props
        out["id"] = iso3
        normalized.append(out)

    result = {
        "type": "FeatureCollection",
        "features": normalized,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1e6:.2f} MB, "
          f"{len(normalized)} features)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
