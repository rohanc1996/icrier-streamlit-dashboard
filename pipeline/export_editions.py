"""Export every edition × score-basis × scaling-method block the site can show.

This is an adapter, in the same family as ``export_web_data.py`` and
``export_overview.py``: every score, rank and weight comes from
``SIDE_dashboard/core`` through the canonical loader. Nothing is re-scaled or
re-rounded here beyond the published conventions.

Why a new file rather than extending ``export_overview.py``: the overview
exporter assumes one edition, 71 scored countries and a fixed 8-pane layout.
The global filter bar needs several editions (one of which, 2024, has 19
countries and 2025 only 38 scored) and three score bases, so the loop is
different even though the primitives are the same.

Output: ``data/derived/web/editions.json`` (checked by
``web/scripts/sync-data.mjs``) plus the raw-data downloads under
``data/derived/web/downloads/``.

    ./.venv/bin/python pipeline/export_editions.py
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "SIDE_dashboard") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "SIDE_dashboard"))

from components.country_names import (  # noqa: E402
    COUNTRY_TO_ISO3,
    short_name,
)
from core import blend, chips  # noqa: E402
from core import chips_hierarchy as H  # noqa: E402
from core import loader, scaling  # noqa: E402

WEB_DIR = REPO_ROOT / "data" / "derived" / "web"
OUT_FILE = WEB_DIR / "editions.json"
DOWNLOAD_DIR = WEB_DIR / "downloads"

# 2027 is deliberately absent: absolute values are incomplete and relative
# denominators are not final. Adding it here is the single switch once the
# edition is signed off.
YEARS = ("2024", "2025", "2026")
METHODS = {"full_minmax": scaling.METHOD_FULL, "z": scaling.METHOD_Z}
BASIS_ORDER = ("absolute", "relative", "combined")

GDP_FILE = REPO_ROOT / "data" / "reference" / "GDP data for SIDE 2027.xlsx - side subset USD.csv"
GDP_YEAR = "2025"
GDP_ISO3_COLUMN = "GDP (current US$)"

# G20 membership, keyed by ISO-3. The export's `BLOC` column is not usable:
# it has 17 rows, includes non-members and omits ten members.
G20 = [
    "ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA",
    "JPN", "MEX", "RUS", "SAU", "ZAF", "KOR", "TUR", "GBR", "USA",
]
# IMF emerging-market members of the G20. Not an official G20 grouping; the
# label in the site says so.
G20_EMERGING = ["ARG", "BRA", "CHN", "IND", "IDN", "MEX", "SAU", "ZAF", "TUR"]


# ---------------------------------------------------------------------------
# JSON-safe primitives
# ---------------------------------------------------------------------------

def num(value):
    if value is None:
        return None
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        value = value.item()
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def integer(value):
    value = num(value)
    return None if value is None else int(value)


def write_json(path: Path, payload: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, allow_nan=False, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return len(text.encode("utf-8")) + 1


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

def load_gdp() -> dict[str, float]:
    raw = pd.read_csv(GDP_FILE, dtype=str, keep_default_na=False)
    frame = loader.shrink_whitespace(raw)
    frame.columns = loader._dedupe_columns(
        pd.Index([loader.normalize_column_name(c) for c in frame.columns])
    )
    iso = frame[GDP_ISO3_COLUMN].astype(str).str.strip()
    values = loader.parse_numeric(frame[GDP_YEAR])
    out: dict[str, float] = {}
    for code, value in zip(iso, values):
        if not code or code.lower().startswith("unnamed"):
            continue
        out[code] = num(value)
    return out


def source_paths(year: str) -> dict[str, Path]:
    """Bases that actually exist for an edition."""
    paths = {}
    absolute = loader.DATASETS[year]["Absolute"]
    relative = loader.DATASETS[year]["Relative"]
    if absolute.exists():
        paths["absolute"] = absolute
    if relative.exists():
        paths["relative"] = relative
    if "absolute" in paths and "relative" in paths:
        paths["combined"] = relative  # placeholder; both are loaded for a blend
    return paths


# ---------------------------------------------------------------------------
# Ranks
# ---------------------------------------------------------------------------

def published_rank(column: pd.Series) -> pd.Series:
    """Rank by the published convention: 2 dp on 0-100, ties share a rank."""
    rounded = (column.astype(float) * 100).round(2) / 100
    return rounded.rank(ascending=False, method="min")


def verdict_points(ranks: list[int], total: int) -> list[dict]:
    """Dot-strip geometry for one pillar's rank distribution.

    Ranks are positions in a fixed pool, so the geometry is identical for every
    country; spreading tied ranks into lanes matches the old pane-4 rule.
    """
    def x(rank: int) -> float:
        return 3 + (rank - 1) / (total - 1) * 94 if total > 1 else 50.0

    groups: dict[int, list[int]] = {}
    for rank in ranks:
        groups.setdefault(rank, []).append(rank)
    seen: dict[int, int] = {}
    points = []
    for rank in ranks:
        index = seen.get(rank, 0)
        seen[rank] = index + 1
        group = groups[rank]
        offset = 0 if len(group) == 1 else (index - (len(group) - 1) / 2) * 5.5
        points.append({
            "rank": rank,
            "xPct": round(x(rank), 4),
            "dy": round(max(-8, min(8, offset)), 3),
        })
    return points


# ---------------------------------------------------------------------------
# One edition × basis × method
# ---------------------------------------------------------------------------

def tables_for(year: str, basis: str, method_key: str):
    """``(table, rel_table, abs_table, data)`` for one combination.

    Returns a blended table for ``combined`` and the single-run table
    otherwise. ``data`` is the dataset the coverage/indicator bookkeeping comes
    from (Relative for a blend, matching the engine's combined view).
    """
    engine_method = METHODS[method_key]
    absolute_path = loader.DATASETS[year]["Absolute"]
    relative_path = loader.DATASETS[year]["Relative"]

    if basis == "combined":
        rel_data = loader.load_app_data(relative_path)
        abs_data = loader.load_app_data(absolute_path)
        rel_pillars, _ = H.resolve_hierarchy(rel_data.numeric_df.columns)
        abs_pillars, _ = H.resolve_hierarchy(abs_data.numeric_df.columns)
        rel_table = chips.chips_table(rel_data, pillars=rel_pillars, method=engine_method)
        abs_table = chips.chips_table(abs_data, pillars=abs_pillars, method=engine_method)
        return blend.blended_chips_table(rel_table, abs_table), rel_table, abs_table, rel_data

    path = relative_path if basis == "relative" else absolute_path
    data = loader.load_app_data(path)
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    table = chips.chips_table(data, pillars=pillars, method=engine_method)
    return table, None, None, data


def build_method_block(year: str, basis: str, method_key: str, gdp: dict[str, float]) -> dict:
    table, rel_table, abs_table, data = tables_for(year, basis, method_key)
    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    pillar_names = [p.name for p in pillars]
    weights = {p.name: float(p.weight) for p in pillars}

    pillar_rank = {name: published_rank(table[name]) for name in pillar_names}
    pillar_of = {name: int(pillar_rank[name].notna().sum()) for name in pillar_names}

    # Per-country engine results give the *effective* weights after a
    # missing-data redistribution, so each contribution reproduces the score
    # even when a pillar was dropped for that country.
    engine_method = METHODS[method_key]
    if basis == "combined":
        rel_data = loader.load_app_data(loader.DATASETS[year]["Relative"])
        abs_data = loader.load_app_data(loader.DATASETS[year]["Absolute"])
        rel_pillars, _ = H.resolve_hierarchy(rel_data.numeric_df.columns)
        abs_pillars, _ = H.resolve_hierarchy(abs_data.numeric_df.columns)
        rel_score_df = chips.score_matrix(rel_data, rel_pillars, method=engine_method)
        abs_score_df = chips.score_matrix(abs_data, abs_pillars, method=engine_method)
        country_results = {}
        for country in rel_data.country_list:
            country_results[country] = (
                chips.aggregate_country(rel_data, country, pillars=rel_pillars, score_df=rel_score_df),
                chips.aggregate_country(abs_data, country, pillars=abs_pillars, score_df=abs_score_df),
            )
    else:
        score_df = chips.score_matrix(data, pillars, method=engine_method)
        country_results = {
            country: (chips.aggregate_country(data, country, pillars=pillars, score_df=score_df), None)
            for country in data.country_list
        }

    table = table.reset_index(drop=True)
    rows = []
    composition = []
    verdict_countries = {}
    size_rows = []

    for index, row in table.iterrows():
        country = row["Country"]
        if country not in COUNTRY_TO_ISO3:
            continue
        iso3 = COUNTRY_TO_ISO3[country]
        score = num(row["chips"])
        rank = integer(row["rank"])
        res_rel, res_abs = country_results[country]

        rows.append({
            "iso3": iso3,
            "country": country,
            "shortName": short_name(country),
            "score": score,
            "rank": rank,
            "coverage": num(row.get("coverage")),
            "indicatorsPresent": integer(row.get("indicators_present")),
            "indicatorsTotal": integer(row.get("indicators_total")),
        })

        contributions = []
        for i, name in enumerate(pillar_names):
            rel_pillar = next(pr for pr in res_rel.pillars if pr.name == name)
            rel_present = [pr for pr in res_rel.pillars if pr.score is not None]
            rel_total_weight = sum(float(pr.nominal_weight) for pr in rel_present) or 1.0
            rel_contrib = (
                None if rel_pillar.score is None
                else float(rel_pillar.score) * float(rel_pillar.nominal_weight) / rel_total_weight
            )
            if res_abs is None:
                contributions.append(rel_contrib)
            else:
                abs_pillar = next(pr for pr in res_abs.pillars if pr.name == name)
                abs_present = [pr for pr in res_abs.pillars if pr.score is not None]
                abs_total_weight = sum(float(pr.nominal_weight) for pr in abs_present) or 1.0
                abs_contrib = (
                    None if abs_pillar.score is None
                    else float(abs_pillar.score) * float(abs_pillar.nominal_weight) / abs_total_weight
                )
                if res_rel.chips.score is not None and res_abs.chips.score is not None:
                    # Both runs scored, so the blend is the mean of the two
                    # totals. A pillar the other run dropped contributes zero
                    # to that side's total: its weight was already redistributed
                    # across the pillars that side does have.
                    contributions.append(
                        ((rel_contrib or 0.0) + (abs_contrib or 0.0)) / 2.0
                    )
                else:
                    contributions.append(blend.blend_value(rel_contrib, abs_contrib))
        if score is not None:
            contribution_sum = sum(c for c in contributions if c is not None)
            if abs(contribution_sum - score) > 5e-4:
                raise AssertionError(
                    f"{year} {basis} {method_key} {country}: contributions sum to "
                    f"{contribution_sum!r}, score is {score!r}"
                )
            composition.append({
                "iso3": iso3,
                "country": country,
                "shortName": short_name(country),
                "rank": rank,
                "score": score,
                "pillars": [
                    {
                        "id": name,
                        "weight": weights[name],
                        "score": num(row[name]),
                        "contribution": contributions[i],
                    }
                    for i, name in enumerate(pillar_names)
                ],
            })

        verdict_pillars = [
            {
                "id": name,
                "score": num(row[name]),
                "rank": integer(pillar_rank[name].iloc[index]),
            }
            for name in pillar_names
        ]
        if score is not None:
            best = min(
                (p for p in verdict_pillars if p["rank"] is not None),
                key=lambda p: (p["rank"], pillar_names.index(p["id"])),
                default=None,
            )
            worst = max(
                (p for p in verdict_pillars if p["rank"] is not None),
                key=lambda p: (p["rank"], -pillar_names.index(p["id"])),
                default=None,
            )
            verdict_countries[iso3] = {
                "iso3": iso3,
                "country": country,
                "shortName": short_name(country),
                "rank": rank,
                "score": score,
                "pillars": verdict_pillars,
                "best": None if best is None else {"id": best["id"], "rank": best["rank"]},
                "worst": None if worst is None else {"id": worst["id"], "rank": worst["rank"]},
            }

        gdp_value = gdp.get(iso3)
        if gdp_value and score is not None:
            size_rows.append({
                "iso3": iso3,
                "country": country,
                "shortName": short_name(country),
                "score": score,
                "rank": rank,
                "gdp": gdp_value,
            })

    rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 10**6, r["iso3"]))
    composition.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 10**6, r["iso3"]))
    size_rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 10**6, r["iso3"]))

    scored = [row for row in rows if row["score"] is not None]
    scores = [row["score"] for row in scored]

    # Verdict geometry is shared by every country: the dots are the pool.
    verdict_pillars = []
    for name in pillar_names:
        ranks = [
            int(v) for v in pillar_rank[name].dropna().tolist()
        ]
        verdict_pillars.append({
            "id": name,
            "of": pillar_of[name],
            "points": verdict_points(sorted(ranks), pillar_of[name]),
            "best": min(ranks) if ranks else None,
            "median": float(np.median(ranks)) if ranks else None,
            "worst": max(ranks) if ranks else None,
        })

    correlation = None
    if len(size_rows) >= 3:
        x = np.log10(np.array([r["gdp"] for r in size_rows], dtype=float))
        y = np.array([r["score"] for r in size_rows], dtype=float)
        correlation = {
            "pearson": round(float(np.corrcoef(x, y)[0, 1]), 4),
            "spearman": round(
                float(np.corrcoef(
                    pd.Series(x).rank(method="average").to_numpy(),
                    pd.Series(y).rank(method="average").to_numpy(),
                )[0, 1]),
                4,
            ),
            "n": len(size_rows),
        }

    return {
        "field": {
            "values": rows,
            "median": float(np.median(scores)) if scores else None,
            "min": float(min(scores)) if scores else None,
            "max": float(max(scores)) if scores else None,
        },
        "composition": composition,
        "verdicts": {"pillars": verdict_pillars, "countries": verdict_countries},
        "sizeVsScore": size_rows,
        "correlation": correlation,
    }


def build_basis(year: str, basis: str, gdp: dict[str, float]) -> dict:
    methods = {key: build_method_block(year, basis, key, gdp) for key in METHODS}

    full = {row["iso3"]: row["rank"] for row in
            methods["full_minmax"]["field"]["values"] if row["rank"] is not None}
    z = {row["iso3"]: row["rank"] for row in
         methods["z"]["field"]["values"] if row["rank"] is not None}
    robustness = []
    for iso3 in sorted(set(full) & set(z)):
        country = next(
            row["country"] for row in methods["full_minmax"]["field"]["values"]
            if row["iso3"] == iso3
        )
        robustness.append({
            "iso3": iso3,
            "country": country,
            "shortName": short_name(country),
            "rankFull": full[iso3],
            "rankZ": z[iso3],
            "delta": z[iso3] - full[iso3],
        })
    robustness.sort(key=lambda r: (abs(r["delta"]), r["country"]))

    leaders = {}
    for method_key, block in methods.items():
        # Pane 4's "pillar leader" is read from this block's verdicts.
        countries = block["verdicts"]["countries"]
        for name in [p["id"] for p in block["verdicts"]["pillars"]]:
            leader = None
            for iso3, item in countries.items():
                pillar = next((p for p in item["pillars"] if p["id"] == name), None)
                if pillar and pillar["rank"] == 1:
                    leader = item["shortName"] or item["country"]
                    break
            leaders.setdefault(method_key, {})[name] = leader

    return {
        "year": year,
        "basis": basis,
        "methods": methods,
        "robustness": robustness,
        "leaders": leaders,
        "countryCount": len(methods["full_minmax"]["field"]["values"]),
        "scoredCount": len([
            r for r in methods["full_minmax"]["field"]["values"] if r["score"] is not None
        ]),
    }


# ---------------------------------------------------------------------------
# Multi-year rank tracker
# ---------------------------------------------------------------------------

def build_tracker(window: list[str], method_key: str) -> dict:
    """Ranks within the countries scored in every selected edition.

    Ranks only — scores are deliberately not included anywhere in this block,
    because the method, indicators and weights change between editions.
    """
    engine_method = METHODS[method_key]
    per_year: dict[str, dict[str, float]] = {}
    names: dict[str, dict[str, str]] = {}

    for year in window:
        data = loader.load_app_data(loader.DATASETS[year]["Absolute"])
        pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
        table = chips.chips_table(data, pillars=pillars, method=engine_method)
        mapping = {}
        for _, row in table.iterrows():
            country = row["Country"]
            if country not in COUNTRY_TO_ISO3 or pd.isna(row["chips"]):
                continue
            iso3 = COUNTRY_TO_ISO3[country]
            mapping[iso3] = float(row["chips"])
            names[iso3] = {"country": country, "shortName": short_name(country)}
        per_year[year] = mapping

    subset = set.intersection(*(set(mapping) for mapping in per_year.values()))
    ranked: dict[str, dict[str, int]] = {}
    for year, mapping in per_year.items():
        series = pd.Series({iso3: mapping[iso3] for iso3 in subset})
        ranks = published_rank(series)
        ranked[year] = {iso3: int(rank) for iso3, rank in ranks.items()}

    countries = []
    for iso3 in subset:
        countries.append({
            "iso3": iso3,
            "country": names[iso3]["country"],
            "shortName": names[iso3]["shortName"],
            "ranks": {year: ranked[year][iso3] for year in window},
        })
    countries.sort(key=lambda r: (r["ranks"][window[-1]], r["country"]))

    return {
        "window": ",".join(window),
        "years": [int(year) for year in window],
        "countries": countries,
        "count": len(countries),
        "note": (
            "Ranks only. The methodology, indicators and weights changed between "
            "editions, so only relative position within a year is comparable."
        ),
    }


def tracker_windows() -> list[list[str]]:
    """Every multi-year selection, not only contiguous runs.

    The year control is a multi-select, so 2024 + 2026 is a valid view even
    though 2025 sits between them.
    """
    from itertools import combinations

    windows: list[list[str]] = []
    for size in range(2, len(YEARS) + 1):
        windows.extend(list(window) for window in combinations(YEARS, size))
    return windows


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------

def write_downloads(editions: dict) -> list[dict]:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    downloads = []

    for year, bases in editions.items():
        for basis, block in bases.items():
            method_key = "full_minmax"
            rows = block["methods"][method_key]["field"]["values"]
            frame = pd.DataFrame([{
                "iso3": row["iso3"],
                "country": row["country"],
                "rank_minmax": row["rank"],
                "chips_score_minmax": row["score"],
                "coverage": row["coverage"],
                "indicators_present": row["indicatorsPresent"],
                "indicators_total": row["indicatorsTotal"],
            } for row in rows])
            # Add the z-score rank alongside.
            z_ranks = {
                row["iso3"]: row["rank"]
                for row in block["methods"]["z"]["field"]["values"]
            }
            frame["rank_z"] = frame["iso3"].map(z_ranks)
            path = DOWNLOAD_DIR / f"side-{year}-{basis}-chips.csv"
            frame.to_csv(path, index=False)
            downloads.append({
                "label": f"SIDE {year} — {basis} scores (CSV)",
                "href": f"/data/{path.name}",
                "note": "One row per country. Scores are 0–100; ranks are 1=best.",
            })

    combined = []
    for year, bases in editions.items():
        for basis, block in bases.items():
            for method_key, block_method in block["methods"].items():
                for row in block_method["field"]["values"]:
                    combined.append({
                        "year": year,
                        "basis": basis,
                        "method": method_key,
                        "iso3": row["iso3"],
                        "country": row["country"],
                        "rank": row["rank"],
                        "chips_score": row["score"],
                        "coverage": row["coverage"],
                    })
    frame = pd.DataFrame(combined)
    path = DOWNLOAD_DIR / "side-all-editions-chips.csv"
    frame.to_csv(path, index=False)
    downloads.append({
        "label": "All editions and bases combined (CSV)",
        "href": f"/data/{path.name}",
        "note": "year, basis and method are columns. Do not compare scores across years.",
    })
    return downloads


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    gdp = load_gdp()
    editions: dict[str, dict] = {}
    availability: dict[str, list[str]] = {}

    for year in YEARS:
        paths = source_paths(year)
        availability[year] = [basis for basis in BASIS_ORDER if basis in paths]
        editions[year] = {}
        for basis in availability[year]:
            editions[year][basis] = build_basis(year, basis, gdp)
            block = editions[year][basis]
            print(
                f"[editions] {year} {basis}: {block['countryCount']} countries, "
                f"{block['scoredCount']} scored, {len(block['robustness'])} rank pairs"
            )

    tracker = {
        method_key: {
            ",".join(window): build_tracker(window, method_key)
            for window in tracker_windows()
        }
        for method_key in METHODS
    }
    for method_key, windows in tracker.items():
        for window, block in windows.items():
            print(f"[tracker] {method_key} {window}: {block['count']} countries")

    leaves = len(H.all_leaves(H.resolve_hierarchy(
        loader.load_app_data(loader.DATASETS[YEARS[-1]]["Absolute"]).numeric_df.columns
    )[0]))

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "years": list(YEARS),
            "methods": list(METHODS),
            "defaultMethod": "z",
            "defaults": {
                "year": YEARS[-1],
                "basis": "combined" if "combined" in availability[YEARS[-1]] else "absolute",
                "group": "all",
                "compare": [],
            },
            "basisOrder": list(BASIS_ORDER),
            "basisAvailability": availability,
            "groups": {
                "all": None,
                "g20": G20,
                "g20em": G20_EMERGING,
            },
            "groupLabels": {
                "all": "All countries",
                "g20": "G20",
                "g20em": "G20 emerging markets",
            },
            "editionCountryCount": {
                year: editions[year][availability[year][0]]["countryCount"]
                for year in YEARS
            },
            "gdpYear": GDP_YEAR,
            "leaves": leaves,
            "edition": YEARS[-1],
        },
        "editions": editions,
        "tracker": tracker,
        "downloads": write_downloads(editions),
    }

    size = write_json(OUT_FILE, payload)
    print(f"[editions] wrote {OUT_FILE.relative_to(REPO_ROOT)} ({size / 1024:.0f} KiB)")


if __name__ == "__main__":
    main()
