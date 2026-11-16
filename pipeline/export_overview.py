"""Export ``data/derived/web/overview.json``: everything the eight-pane carousel needs.

This is another *adapter* in the same family as ``export_web_data.py``: every
score, rank and weight comes from the engine (``SIDE_dashboard/core/``) through
the canonical loader, and nothing is re-scaled, re-rounded or re-ranked here.
The site must never have to join or rank in JavaScript, so each pane gets a
ready-made array.

Contract (see ``pipeline/schema/overview.schema.json``)::

    meta            the edition exported, its methods, the default method,
                    countries and GDP year
    methods         one block per scaling method, identical shape::
                      methods["z"] / methods["full_minmax"]
                        field        all 71 scores + median/min/max (pane 1)
                        top15        ranks 1-15 (pane 2)
                        composition  top 10, five weighted contributions (pane 3)
                        india        India's five pillar scores/ranks (pane 4)
                        movement     ranks + scores by edition, plus pool (pane 5)
                        sizeVsScore  CHIPS score x GDP 2025 nominal USD (pane 7)
                        coverage     score x data coverage (pane 8)
                        correlation  log10(GDP) against score (pane 7 caption)
    scaleMovement   overall rank under both methods, all 71 (pane 6). Inherently
                    cross-method, so it stays at the top level.

The site switches methods by swapping blocks; it never re-scores or re-ranks.
``meta.defaultMethod`` is ``z`` — a deliberate product change — and every
score in ``methods`` is computed with that method's own scaling.

Scores are 0-1 throughout; the site multiplies by 100 for display. Ranks are
1-based competition ranks (ties share the minimum), exactly as the engine
publishes them.

``movement`` carries both numbers per country and the pool it is ranked
against, so pane 5 needs no join back to ``series.json``::

    movement.pool              {"2025": 59, "2026": 71}
    movement.countries[]       { iso3, country,
                                 ranks:  {"2025": n|null, "2026": n|null},
                                 scores: {"2025": x|null, "2026": x|null} }

``pool`` is the number of countries the edition carries (the field a rank is
out of), derived from ``data.country_list`` through the canonical loader. It is
not the number of countries that score: the 2025 edition carries 59 names but
only 38 with a CHIPS score, so ``pool["2025"]`` is 59 while the non-null scores
in that year number 38.

Two deliberate choices worth knowing:

* **The movement year window is not hard-coded.** It is the union of the edition
  window the web export already publishes (``series.json`` ``meta.years``) and
  the editions that already have a ``data/derived/web/<year>/chips.json``.
  Today that is 2025-2026; when 2027 lands, regenerating either artefact adds
  it with no code change. ``--years`` overrides it for experiments.
* **``gdpPerCapita`` is ``null``.** No population series exists in the repo, and
  the exporter will not invent one. The GDP reference is joined on ISO-3 from
  ``data/reference/GDP data for SIDE 2027.xlsx - side subset USD.csv``, column
  ``2025`` (current US$).

Usage::

    ./.venv/bin/python pipeline/export_overview.py            # write + report
    ./.venv/bin/python pipeline/export_overview.py --no-report
"""

from __future__ import annotations

import argparse
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
from core import chips  # noqa: E402
from core import chips_hierarchy as H  # noqa: E402
from core import loader, scaling  # noqa: E402

EDITION = "2026"
DEFAULT_METHOD_KEY = "z"
JSON_METHODS = {
    "full_minmax": scaling.METHOD_FULL,
    "z": scaling.METHOD_Z,
}
METHOD_ORDER = list(JSON_METHODS)

WEB_DIR = REPO_ROOT / "data" / "derived" / "web"
SERIES_FILE = WEB_DIR / "series.json"
OUT_FILE = WEB_DIR / "overview.json"
CHIPS_FILE = WEB_DIR / EDITION / "chips.json"

GDP_FILE = REPO_ROOT / "data" / "reference" / "GDP data for SIDE 2027.xlsx - side subset USD.csv"
GDP_YEAR = "2025"
GDP_SOURCE = "data/reference/GDP data for SIDE 2027.xlsx - side subset USD.csv"
GDP_ISO3_COLUMN = "GDP (current US$)"  # the source sheet's ISO-3 column (mis-headed)
GDP_ROW_COUNTRY_COLUMN = "Country Name"

REPORT = REPO_ROOT / "deliverables" / "website-prototype" / "overview-report.md"

FIELD_COUNT = 71
TOP_N = 15
COMPOSITION_N = 10
COMPOSITION_TOLERANCE = 1e-9


# ---------------------------------------------------------------------------
# JSON-safe primitives (same helpers as export_web_data.py; NaN is not JSON)
# ---------------------------------------------------------------------------

def num(value):
    """A JSON-safe float, or ``None`` for missing / non-finite values."""
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
    """A JSON-safe int, or ``None``."""
    value = num(value)
    return None if value is None else int(value)


def cell(value) -> str:
    return "null" if value is None else repr(value)


def write_json(path: Path, payload: dict) -> int:
    """Minified, ``allow_nan=False``. Returns the byte count written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, allow_nan=False, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return len(text.encode("utf-8")) + 1


# ---------------------------------------------------------------------------
# Editions and methods
# ---------------------------------------------------------------------------

def load_edition(year: str):
    path = loader.DATASETS[year]["Absolute"]
    if not path.exists():
        raise FileNotFoundError(f"no Absolute file for edition {year}: {path}")
    return path, loader.load_app_data(path)


def score_edition(year: str, engine_method: str = scaling.METHOD_FULL):
    """``(data, pillars, table)`` for one edition through the engine."""
    _path, data = load_edition(year)
    pillars, _unresolved = H.resolve_hierarchy(data.numeric_df.columns)
    table = chips.chips_table(data, pillars=pillars, method=engine_method)
    return data, pillars, table


def movement_years(override: list[str] | None = None) -> list[str]:
    """Editions the movement pane spans, derived rather than listed.

    The window is the **union of the editions the web export already publishes**:

    * ``series.json`` ``meta.years`` — the ladder's edition window, and
    * every ``data/derived/web/<year>/chips.json`` — an edition exported for
      the site.

    No count and no year is written into the movement code, so a new edition is
    picked up by regenerating either artefact: the list, the rank keys and the
    country count all follow. ``--years`` overrides it for experiments.
    """
    if override:
        years = [str(y).strip() for y in override]
    else:
        years: list[str] = []
        if SERIES_FILE.exists():
            years += [str(y) for y in
                      json.loads(SERIES_FILE.read_text(encoding="utf-8"))["meta"]["years"]]
        years += [path.parent.name for path in sorted(WEB_DIR.glob("*/chips.json"))]
        if not years:
            years = [y for y in loader.available_years()
                     if loader.DATASETS[y]["Absolute"].exists()]
    missing = [y for y in years if not loader.DATASETS[y]["Absolute"].exists()]
    if missing:
        raise FileNotFoundError(
            f"movement window names editions with no Absolute file: {missing}"
        )
    return sorted(dict.fromkeys(years), key=int)


# ---------------------------------------------------------------------------
# External context: GDP
# ---------------------------------------------------------------------------

def load_gdp() -> dict[str, float]:
    """ISO-3 -> 2025 GDP (current US$), read with the canonical CSV helpers.

    The source sheet's third column is headed "GDP (current US$)" but holds
    ISO-3 codes; the year columns (``2019`` ... ``2025``) hold the values.
    """
    raw = pd.read_csv(GDP_FILE, dtype=str, keep_default_na=False)
    frame = loader.shrink_whitespace(raw)
    frame.columns = loader._dedupe_columns(
        pd.Index([loader.normalize_column_name(c) for c in frame.columns])
    )
    if GDP_YEAR not in frame.columns:
        raise KeyError(f"{GDP_FILE.name}: no {GDP_YEAR!r} column; has {list(frame.columns)}")
    iso = frame[GDP_ISO3_COLUMN].astype(str).str.strip()
    values = loader.parse_numeric(frame[GDP_YEAR])
    out: dict[str, float] = {}
    for code, value in zip(iso, values):
        if not code or code.lower().startswith("unnamed"):
            continue
        out[code] = num(value)
    return out


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------

def series_scores(method_key: str = DEFAULT_METHOD_KEY) -> dict[tuple[str, str], float | None]:
    """``(iso3, "year") -> overall`` for one method's ladder in ``series.json``.

    Each method block carries its own ``movement``, so the pane-5 check reads
    the matching method's ladder rather than only the default's (the overalls
    differ by method).
    """
    if not SERIES_FILE.exists():
        return {}
    payload = json.loads(SERIES_FILE.read_text(encoding="utf-8"))
    rows = payload.get("methods", {}).get(method_key, {}).get("series", [])
    return {(row["iso3"], str(row["year"])): row["overall"] for row in rows}


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.corrcoef(x, y)[0, 1])


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman as Pearson on average ranks (no scipy in this venv)."""
    rx = pd.Series(x).rank(method="average").to_numpy()
    ry = pd.Series(y).rank(method="average").to_numpy()
    return _pearson(rx, ry)


def correlation_block(size_rows: list[dict], top_gdp_iso3: set[str]) -> dict:
    """Pane 7's caption number: log10(GDP) against the CHIPS score.

    Computed from the 71 rows in this method's ``sizeVsScore``; the ``ExTop2``
    pair drops the two largest economies (USA and China), which are the two
    points that dominate a log-x fit. Rounded to 4 dp.
    """
    x = np.log10(np.array([row["gdp"] for row in size_rows], dtype=float))
    y = np.array([row["score"] for row in size_rows], dtype=float)
    keep = np.array([row["iso3"] not in top_gdp_iso3 for row in size_rows])
    return {
        "pearson": round(_pearson(x, y), 4),
        "spearman": round(_spearman(x, y), 4),
        "pearsonExTop2": round(_pearson(x[keep], y[keep]), 4),
        "spearmanExTop2": round(_spearman(x[keep], y[keep]), 4),
        "n": len(size_rows),
    }


def build_method_block(edition: str, method_key: str, window: list[str],
                       gdp: dict[str, float],
                       top_gdp_iso3: set[str]) -> tuple[dict, dict]:
    """One method's version of every method-dependent pane.

    Everything the carousel renders except ``scaleMovement`` (which is
    inherently cross-method) is rebuilt here under ``method_key``, so the site
    switches panes by swapping blocks and never recomputes a score.
    """
    engine_method = JSON_METHODS[method_key]
    data, pillars, table = score_edition(edition, engine_method)
    score_df = chips.score_matrix(data, pillars, method=engine_method)
    pillar_names = [p.name for p in pillars]

    # Pillar ranks use the exporter's published rule: score rounded to 2 dp on
    # the 0-100 scale, then rank(ascending=False, method="min").
    pillar_rank = {
        name: ((table[name].astype(float) * 100).round(2) / 100)
        .rank(ascending=False, method="min")
        for name in pillar_names
    }
    pillar_of = {
        name: int(pillar_rank[name].notna().sum()) for name in pillar_names
    }

    rows = []
    composition = []
    composition_residuals: list[float] = []
    composition_rounding: list[float] = []
    coverage_rows = []
    india = None

    for i, country in enumerate(data.country_list):
        res = chips.aggregate_country(data, country, pillars=pillars, score_df=score_df)
        iso3 = COUNTRY_TO_ISO3[country]
        score = num(res.chips.score)
        rank = integer(table["rank"].iloc[i])
        row = {
            "iso3": iso3,
            "country": country,
            "shortName": short_name(country),
            "score": score,
            "rank": rank,
        }
        rows.append(row)

        coverage_rows.append({
            "iso3": iso3,
            "country": country,
            "score": score,
            "rank": rank,
            "coverage": num(res.coverage["coverage"]),
            "indicatorsPresent": integer(res.coverage["indicators_present"]),
            "indicatorsTotal": integer(res.coverage["indicators_total"]),
        })

        # Weighted pillar decomposition. The five contributions must reproduce
        # the *unrounded* composite; the engine rounds the published score to
        # 2 dp on the 0-100 scale afterwards.
        contributions = []
        for pillar_result in res.pillars:
            spec_weight = next(p.weight for p in pillars if p.name == pillar_result.name)
            if pillar_result.score is None:
                contributions.append(None)
                continue
            contributions.append(float(pillar_result.score) * float(spec_weight))
        if all(c is not None for c in contributions):
            unrounded = sum(contributions)
            residual = abs(unrounded - sum(
                float(pr.score) * float(pr.nominal_weight) for pr in res.pillars))
            composition_residuals.append(residual)
            if residual >= COMPOSITION_TOLERANCE:
                raise AssertionError(
                    f"{country}: weighted pillar contributions differ from the "
                    f"unrounded composite by {residual!r}"
                )
            # The engine's published score is that sum, rounded to 2 dp on 0-100.
            engine_rounded = round(unrounded * 100, 2) / 100
            if score is None or abs(engine_rounded - score) > 1e-12:
                raise AssertionError(
                    f"{country}: nominal weights give {engine_rounded!r}, engine "
                    f"published {score!r}"
                )
            composition_rounding.append(abs(unrounded - score))

        if country == "India":
            pillar_payload = []
            for name in pillar_names:
                pillar_payload.append({
                    "id": name,
                    "score": num(next(pr.score for pr in res.pillars if pr.name == name)),
                    "rank": integer(pillar_rank[name].iloc[i]),
                    "of": pillar_of[name],
                })
            best = min(pillar_payload, key=lambda p: (p["rank"], pillar_names.index(p["id"])))
            worst = max(pillar_payload, key=lambda p: (p["rank"], -pillar_names.index(p["id"])))
            india = {
                "iso3": iso3,
                "country": country,
                "rank": rank,
                "score": score,
                "pillars": pillar_payload,
                "best": {"id": best["id"], "rank": best["rank"]},
                "worst": {"id": worst["id"], "rank": worst["rank"]},
            }

    if len(rows) != FIELD_COUNT:
        raise AssertionError(f"{edition} has {len(rows)} countries, expected {FIELD_COUNT}")
    if len({row["iso3"] for row in rows}) != len(rows):
        raise AssertionError("duplicate ISO-3 code in the field")
    if any(row["score"] is None or row["rank"] is None for row in rows):
        raise AssertionError(f"{edition} has an unscored country; the carousel needs all 71")
    if india is None:
        raise AssertionError("India not found in the edition")

    rows.sort(key=lambda r: (r["rank"], r["iso3"]))

    # ---- field (pane 1) --------------------------------------------------
    scores = [row["score"] for row in rows]
    field = {
        "median": float(np.median(scores)),
        "min": float(min(scores)),
        "max": float(max(scores)),
        "values": rows,
    }

    # ---- top 15 (pane 2) -------------------------------------------------
    top15 = [row for row in rows if row["rank"] <= TOP_N]

    # ---- composition (pane 3) -------------------------------------------
    composition = []
    for row in rows[:COMPOSITION_N]:
        country = row["country"]
        index = data.country_list.index(country)
        res = chips.aggregate_country(data, country, pillars=pillars, score_df=score_df)
        composition.append({
            "iso3": row["iso3"],
            "country": country,
            "rank": row["rank"],
            "score": row["score"],
            "pillars": [
                {
                    "id": name,
                    "score": num(next(pr.score for pr in res.pillars if pr.name == name)),
                    "weight": num(next(p.weight for p in pillars if p.name == name)),
                    "contribution": float(next(pr.score for pr in res.pillars
                                                if pr.name == name))
                    * float(next(p.weight for p in pillars if p.name == name)),
                }
                for name in pillar_names
            ],
        })

    # ---- movement (pane 5), N editions ----------------------------------
    rank_by_year: dict[str, dict[str, int | None]] = {}
    score_by_year: dict[str, dict[str, float | None]] = {}
    pool_by_year: dict[str, int] = {}
    scored_per_year: dict[str, int] = {}
    names = {row["iso3"]: row["country"] for row in rows}
    for year in window:
        year_data, year_pillars, year_table = score_edition(year, engine_method)
        year_ranks: dict[str, int | None] = {}
        year_scores: dict[str, float | None] = {}
        for i, country in enumerate(year_data.country_list):
            iso3 = COUNTRY_TO_ISO3[country]
            year_ranks[iso3] = integer(year_table["rank"].iloc[i])
            year_scores[iso3] = num(year_table["chips"].iloc[i])
            names.setdefault(iso3, country)
        rank_by_year[year] = year_ranks
        score_by_year[year] = year_scores
        # The pool is the edition's field size (the countries a rank is out
        # of), taken from the loader's country list -- never from a CSV header.
        pool_by_year[year] = len(year_data.country_list)
        scored_per_year[year] = sum(1 for v in year_scores.values() if v is not None)

    movement_countries = []
    for iso3 in sorted(names):
        ranks = {year: rank_by_year[year].get(iso3) for year in window}
        if sum(1 for value in ranks.values() if value is not None) >= 2:
            movement_countries.append({
                "iso3": iso3,
                "country": names[iso3],
                "ranks": ranks,
                "scores": {year: score_by_year[year].get(iso3) for year in window},
            })
    movement_countries.sort(key=lambda r: r["iso3"])

    movement = {
        "years": [int(y) for y in window],
        "pool": {str(y): pool_by_year[y] for y in window},
        "scorableYears": sum(1 for y in window if scored_per_year[y] > 0),
        "countries": movement_countries,
    }

    # Cross-check the new scores against the ladder the site already plots.
    # Exact float equality, no tolerance: both sides are the engine's 4-dp
    # (2-dp on 0-100) rounded composite.
    series = series_scores(method_key)
    series_compared = 0
    series_mismatches: list[dict] = []
    for row in movement_countries:
        for year in window:
            key = (row["iso3"], str(year))
            if key not in series:
                continue
            expected = series[key]
            actual = row["scores"][str(year)]
            series_compared += 1
            if actual != expected:
                series_mismatches.append({
                    "iso3": row["iso3"], "year": str(year),
                    "overview": actual, "series": expected,
                })

    # ---- sizeVsScore (pane 7) -------------------------------------------
    missing_gdp = [row["iso3"] for row in rows if row["iso3"] not in gdp]
    if missing_gdp:
        raise AssertionError(f"GDP reference has no row for {missing_gdp}")
    size_vs_score = [
        {
            "iso3": row["iso3"],
            "country": row["country"],
            "score": row["score"],
            "rank": row["rank"],
            "gdp": gdp[row["iso3"]],
            "gdpPerCapita": None,
        }
        for row in rows
    ]
    gdp_join = len(size_vs_score)

    coverage_rows.sort(key=lambda r: (r["rank"], r["iso3"]))

    correlation = correlation_block(size_vs_score, top_gdp_iso3)

    block = {
        "field": field,
        "top15": top15,
        "composition": composition,
        "india": india,
        "movement": movement,
        "sizeVsScore": size_vs_score,
        "coverage": coverage_rows,
        "correlation": correlation,
    }

    measurements = {
        "edition": edition,
        "method": method_key,
        "countries": len(rows),
        "field": len(field["values"]),
        "top15": len(top15),
        "top15MaxRank": max(row["rank"] for row in top15),
        "composition": len(composition),
        "compositionResidual": max(composition_residuals),
        "compositionRounding": max(composition_rounding),
        "movementYears": [int(y) for y in window],
        "movementPool": {int(y): pool_by_year[y] for y in window},
        "movementCountries": len(movement_countries),
        "scoredPerYear": {int(y): scored_per_year[y] for y in window},
        "movementSeriesCompared": series_compared,
        "movementSeriesMismatches": series_mismatches,
        "gdpJoin": len(size_vs_score),
        "gdpMissing": missing_gdp,
        "sizeVsScore": len(size_vs_score),
        "coverage": len(coverage_rows),
        "correlation": correlation,
        "india": india,
        "top3": rows[:3],
    }
    return block, measurements


def build_payload(edition: str = EDITION, years: list[str] | None = None) -> tuple[dict, dict]:
    """Build the carousel document plus the measurements the report needs."""
    window = movement_years(years)
    gdp = load_gdp()

    # The pane 7 caption excludes the two largest economies; they are found
    # from the GDP column, not typed in, and asserted to be USA and China.
    top_gdp_iso3 = set(sorted(gdp, key=lambda code: gdp[code], reverse=True)[:2])
    if top_gdp_iso3 != {"USA", "CHN"}:
        raise AssertionError(
            f"the two largest GDP rows are {sorted(top_gdp_iso3)}, expected USA and CHN"
        )

    methods: dict[str, dict] = {}
    stats: dict[str, dict] = {}
    for method_key in METHOD_ORDER:
        block, block_stats = build_method_block(
            edition, method_key, window, gdp, top_gdp_iso3
        )
        methods[method_key] = block
        stats[method_key] = block_stats

    # Every block must describe the same field, so the toggle swaps numbers
    # without changing the layout.
    counts = {
        key: (
            len(block["field"]["values"]), len(block["top15"]),
            len(block["composition"]), len(block["india"]["pillars"]),
            len(block["movement"]["countries"]), len(block["sizeVsScore"]),
            len(block["coverage"]),
        )
        for key, block in methods.items()
    }
    if len({value for value in counts.values()}) != 1:
        raise AssertionError(f"method blocks have different row counts: {counts}")
    for key in METHOD_ORDER:
        block = methods[key]
        if block["movement"]["pool"] != methods[METHOD_ORDER[0]]["movement"]["pool"]:
            raise AssertionError(f"{key}: movement.pool differs between methods")
        if block["india"]["pillars"][0]["of"] != methods[METHOD_ORDER[0]]["india"]["pillars"][0]["of"]:
            raise AssertionError(f"{key}: pillar field sizes differ between methods")

    # ---- scaleMovement (pane 6), cross-method ----------------------------
    rank_full = {row["iso3"]: row["rank"] for row in methods["full_minmax"]["field"]["values"]}
    rank_z = {row["iso3"]: row["rank"] for row in methods["z"]["field"]["values"]}
    names = {row["iso3"]: row["country"]
             for row in methods["full_minmax"]["field"]["values"]}
    movers = [
        {
            "iso3": iso3,
            "country": names[iso3],
            "rankFull": rank_full[iso3],
            "rankZ": rank_z[iso3],
            "delta": rank_z[iso3] - rank_full[iso3],
        }
        for iso3 in rank_full
        if rank_full[iso3] is not None and rank_z.get(iso3) is not None
    ]
    movers.sort(key=lambda r: (-abs(r["delta"]), r["rankFull"], r["iso3"]))
    if len(movers) != len(rank_full):
        raise AssertionError(
            f"scaleMovement has {len(movers)} movers for {len(rank_full)} countries"
        )
    scale_movement = {"pairs": METHOD_ORDER, "movers": movers}

    # Where the two methods disagree: overall ranks, and which countries make
    # the top 15. Reported, never "fixed".
    rank_diffs = [m for m in movers if m["delta"] != 0]
    top15_full = {row["iso3"] for row in methods["full_minmax"]["top15"]}
    top15_z = {row["iso3"] for row in methods["z"]["top15"]}
    top15_diffs = {
        "out": sorted(top15_full - top15_z),
        "in": sorted(top15_z - top15_full),
    }

    payload = {
        "meta": {
            "edition": edition,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "methods": METHOD_ORDER,
            "defaultMethod": DEFAULT_METHOD_KEY,
            "countries": len(methods[DEFAULT_METHOD_KEY]["field"]["values"]),
            "gdpYear": int(GDP_YEAR),
            "gdpSource": GDP_SOURCE,
        },
        "methods": methods,
        "scaleMovement": scale_movement,
    }

    measurements = {
        "edition": edition,
        "generated": payload["meta"]["generated"],
        "defaultMethod": DEFAULT_METHOD_KEY,
        "countries": payload["meta"]["countries"],
        "methods": stats,
        "methodCounts": counts,
        "movers": len(movers),
        "worstMovers": movers[:3],
        "rankDiffs": len(rank_diffs),
        "top15Diffs": top15_diffs,
    }
    return payload, measurements


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _chips_reference() -> dict | None:
    """``chips.json`` keyed by method, for the spot check in the report."""
    if not CHIPS_FILE.exists():
        return None
    payload = json.loads(CHIPS_FILE.read_text(encoding="utf-8"))
    return {
        "by_method": {
            method: {row["iso3"]: row for row in payload["methods"][method]["scores"]}
            for method in METHOD_ORDER
        },
        "path": CHIPS_FILE,
    }


def write_report(path: Path, payload: dict, size_bytes: int, measurements: dict) -> None:
    reference = _chips_reference()
    meta = payload["meta"]
    methods = payload["methods"]
    stats = measurements["methods"]
    counts = measurements["methodCounts"]
    lines = [
        "# Overview carousel export report",
        "",
        f"Generated by `pipeline/export_overview.py` on {meta['generated']}.",
        "",
        f"- File: `{OUT_FILE.relative_to(REPO_ROOT)}`",
        f"- Size: **{size_bytes} bytes** ({size_bytes / 1024:.1f} KB), minified, "
        "`allow_nan=False`",
        f"- Edition: **{meta['edition']} Absolute**, default method "
        f"`{meta['defaultMethod']}`, countries **{meta['countries']}**",
        f"- Methods in the payload: `{meta['methods']}`, one full block each",
        f"- GDP context: {meta['gdpYear']} nominal US$ from "
        f"`{meta['gdpSource']}`",
        "",
        "All scores are 0-1 (the site multiplies by 100). Ranks are 1-based "
        "competition ranks; ties share the minimum.",
        "",
        "## Shape",
        "",
        "```",
        "meta          { edition, generated, methods, defaultMethod, countries, gdpYear, gdpSource }",
        "methods       { \"z\": {...}, \"full_minmax\": {...} }",
        "scaleMovement { pairs, movers }",
        "```",
        "",
        "Each block under `methods` carries `field`, `top15`, `composition`, "
        "`india`, `movement`, `sizeVsScore`, `coverage` and `correlation`, all "
        "scored under that method. `scaleMovement` is inherently cross-method and "
        "stays at the top level. The overview toggle swaps blocks; the frontend "
        "never re-scores or re-ranks.",
        "",
        "`meta.defaultMethod` is **`z`**. That is a deliberate product change: "
        "the overview opens on the z-scored league table, and no block anywhere "
        "in the payload treats min-max as the default.",
        "",
        "## Counts (identical in both blocks)",
        "",
        "| Array | `z` | `full_minmax` | Pane |",
        "| --- | --- | --- | --- |",
    ]
    labels = [
        ("field.values", "1. The field"),
        ("top15", "2. The podium and the pack"),
        ("composition", "3. Anatomy of a score"),
        ("india.pillars", "4. India's five verdicts"),
        ("movement.countries", "5. Movement"),
        ("sizeVsScore", "7. Scale and score"),
        ("coverage", "8. How much stands behind a score"),
    ]
    for index, (label, pane) in enumerate(labels):
        lines.append(
            f"| `{label}` | {counts['z'][index]} | {counts['full_minmax'][index]} "
            f"| {pane} |"
        )
    lines += [
        f"| `scaleMovement.movers` | {measurements['movers']} | "
        f"{measurements['movers']} | 6. The same index, two scales |",
        "",
        "The exporter asserts the counts agree across methods, so the toggle can "
        "never change the layout: 71 field rows, 15 top-15 rows, 10 composition "
        "rows, 5 India pillars, the same movement country count, 71 "
        "`sizeVsScore` rows and 71 `coverage` rows per block.",
        "",
        "## The two methods disagree — as intended (pane 6)",
        "",
        f"- `pairs`: `{payload['scaleMovement']['pairs']}`; "
        "`delta = rankZ - rankFull`, sorted by absolute delta.",
        f"- **{measurements['rankDiffs']} of {measurements['movers']} countries "
        "change overall rank between methods.** That is engine behaviour, pinned "
        "by `SIDE_dashboard/core/rankings.py::composite_scaling_comparison`: "
        "per-indicator ranks cannot move (monotone transforms), but the "
        "composite is a weighted sum of differently shaped transforms, so "
        "overall ranks can.",
        f"- Top-15 membership changes: **{len(measurements['top15Diffs']['out'])} "
        "out / "
        f"{len(measurements['top15Diffs']['in'])} in** "
        f"(in the full_minmax top 15 but not the z top 15: "
        f"{measurements['top15Diffs']['out'] or 'none'}; in the z top 15 but not "
        f"full_minmax: {measurements['top15Diffs']['in'] or 'none'}).",
        "",
        "| Country | ISO-3 | full_minmax rank | z rank | delta |",
        "| --- | --- | --- | --- | --- |",
    ]
    for mover in measurements["worstMovers"]:
        lines.append(
            f"| {mover['country']} | {mover['iso3']} | {mover['rankFull']} "
            f"| {mover['rankZ']} | {mover['delta']:+} |"
        )
    lines += [
        "",
        "## Pane 7 correlation: log10(GDP) against score",
        "",
        "Computed from this method's own `sizeVsScore` scores over all 71 rows "
        "(GDP is method-independent, the scores are not). `ExTop2` drops the "
        "two largest economies, USA and China, which dominate a log-x fit. "
        "Rounded to 4 dp; Spearman is Pearson on average ranks, so no scipy is "
        "needed.",
        "",
        "| Method | Pearson | Spearman | Pearson ex-Top2 | Spearman ex-Top2 | n |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for method in METHOD_ORDER:
        corr = methods[method]["correlation"]
        lines.append(
            f"| `{method}` | {corr['pearson']:.4f} | {corr['spearman']:.4f} "
            f"| {corr['pearsonExTop2']:.4f} | {corr['spearmanExTop2']:.4f} "
            f"| {corr['n']} |"
        )
    lines += [
        "",
        "## Movement and `series.json` (pane 5)",
        "",
        "Each block's `movement.scores` is compared with the matching method's "
        "`overall` ladder in `data/derived/web/series.json`, for the same ISO-3 "
        "and edition. Exact float equality, no tolerance: both sides are the "
        "engine's rounded composite.",
        "",
        "| Method | Pairs compared | Mismatches |",
        "| --- | --- | --- |",
    ]
    for method in METHOD_ORDER:
        s = stats[method]
        lines.append(
            f"| `{method}` | {s['movementSeriesCompared']} "
            f"| {len(s['movementSeriesMismatches'])} |"
        )
    for method in METHOD_ORDER:
        for mismatch in stats[method]["movementSeriesMismatches"]:
            lines.append(
                f"  - `{method}` {mismatch['iso3']} {mismatch['year']}: overview "
                f"`{cell(mismatch['overview'])}` vs series "
                f"`{cell(mismatch['series'])}`"
            )
    first = stats[METHOD_ORDER[0]]
    lines += [
        "",
        f"- Years in both blocks: **{first['movementYears']}** "
        "(`movement.years`, ascending integers).",
        f"- `movement.scorableYears`: **{methods['z']['movement']['scorableYears']}** "
        "editions in the window produced at least one score.",
        f"- Countries scored in at least two editions: **{first['movementCountries']}** "
        "(the same set in both methods, so the pane does not change length).",
        "- Pool per edition (`movement.pool`, the number of countries the "
        "edition carries, taken from `data.country_list` through the canonical "
        "loader — not counted from a CSV header): "
        + ", ".join(f"{year}: {count}"
                    for year, count in first["movementPool"].items())
        + ". Identical in both blocks: the pool is the field a rank is out of, "
        "not the number scored (2025 carries 59 names, 38 of them scored).",
        "- Scored countries per edition (non-null `scores`): "
        + ", ".join(f"{year}: {count}"
                    for year, count in first["scoredPerYear"].items())
        + ".",
        "- Each `movement.countries[]` row is "
        "`{iso3, country, ranks: {year: n|null}, scores: {year: x|null}}`, so "
        "pane 5 needs no join back to `series.json`.",
        "- The window is derived, not hard-coded: `movement_years()` takes the "
        "union of `series.json` `meta.years` and every edition that already has "
        "a `data/derived/web/<year>/chips.json`.",
        "",
        "## Composition residual (pane 3)",
        "",
        "`composition.pillars[].contribution = nominal pillar weight x pillar "
        "score` with the published weights 0.25/0.25/0.25/0.125/0.125. Each "
        "country's five contributions must sum to its unrounded composite; the "
        "engine then rounds the published score to 2 dp on the 0-100 scale.",
        "",
        "| Method | Worst residual (tolerance 1e-9) | Largest rounding distance |",
        "| --- | --- | --- |",
    ]
    for method in METHOD_ORDER:
        s = stats[method]
        lines.append(
            f"| `{method}` | `{s['compositionResidual']:.3e}` "
            f"| `{s['compositionRounding']:.3e}` |"
        )
    lines += [
        "",
        "The exporter also recomputes `round(sum x 100, 2) / 100` from the "
        "nominal weights and asserts it equals the engine's published score "
        "exactly, for both methods.",
        "",
        "## India under each method (pane 4)",
        "",
        "| Pillar | `z` score | `z` rank | full_minmax score | full_minmax rank | of |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    z_india = methods["z"]["india"]
    full_india = methods["full_minmax"]["india"]
    for zp, fp in zip(z_india["pillars"], full_india["pillars"]):
        r = lambda value: "null" if value is None else str(value)
        score_z = "null" if zp["score"] is None else f"{zp['score'] * 100:.2f}"
        score_f = "null" if fp["score"] is None else f"{fp['score'] * 100:.2f}"
        lines.append(
            f"| {zp['id']} | {score_z} | {r(zp['rank'])} | {score_f} "
            f"| {r(fp['rank'])} | {zp['of']} |"
        )
    lines += [
        "",
        f"- `z`: overall rank **{z_india['rank']}**, score "
        f"`{z_india['score']:.4f}`; best **{z_india['best']['id']}** "
        f"(rank {z_india['best']['rank']}), worst "
        f"**{z_india['worst']['id']}** (rank {z_india['worst']['rank']}).",
        f"- `full_minmax`: overall rank **{full_india['rank']}**, score "
        f"`{full_india['score']:.4f}`; best **{full_india['best']['id']}** "
        f"(rank {full_india['best']['rank']}), worst "
        f"**{full_india['worst']['id']}** (rank {full_india['worst']['rank']}).",
    ]
    changed_ids = (z_india["best"]["id"] != full_india["best"]["id"]
                   or z_india["worst"]["id"] != full_india["worst"]["id"])
    moved_ranks = (z_india["best"]["rank"] != full_india["best"]["rank"]
                   or z_india["worst"]["rank"] != full_india["worst"]["rank"])
    lines += [
        ("- **India's best and/or worst pillar change between methods** — pane 4's "
         "copy that names them must be method-aware."
         if changed_ids else
         "- India's best and worst pillars are the **same pillars** under both "
         "methods (" + z_india["best"]["id"] + " best, "
         + z_india["worst"]["id"] + " worst), so pane 4's copy can still name "
         "them; only their ranks move"
         + (" — see the table above." if moved_ranks else " (not at all here).")),
        "- Scores are shown on the 0-100 scale for readability; the payload keeps "
        "0-1. `of` is the number of countries that competed in that pillar rank "
        "and is identical in both blocks.",
        "",
        "## GDP join (pane 7)",
        "",
        f"- Source: `{GDP_SOURCE}`, column `{GDP_YEAR}` (current US$).",
        "- The sheet's ISO-3 codes sit under the column headed "
        "`GDP (current US$)`, and the year columns hold the values. The join is "
        "ISO-3 only, no name matching.",
        f"- **All {stats['z']['gdpJoin']} of {measurements['countries']} ISO-3 "
        "codes matched; 0 missing.** The exporter asserts this and fails "
        "otherwise.",
        "- `sizeVsScore[].gdp` is identical country by country in both blocks "
        "(GDP does not depend on scaling, though the rows are ordered by each "
        "method's rank); only `score` and `rank` differ.",
        "- `gdpPerCapita` is `null` for every row: the repo has no population "
        "series, and the exporter does not invent one.",
        "",
        "## Spot check against `chips.json`",
        "",
    ]

    if reference is None:
        lines.append(
            f"`{CHIPS_FILE.relative_to(REPO_ROOT)}` is missing, so no spot check "
            "was possible. Run `pipeline/export_web_data.py` first."
        )
        checks_ok = None
    else:
        checks_ok = True
        lines += [
            f"Reference: `{reference['path'].relative_to(REPO_ROOT)}`, both "
            "methods. Values are compared exactly, not at a tolerance.",
            "",
            "| Method | `field.values` | India pillars | Top 3 |",
            "| --- | --- | --- | --- |",
        ]
        for method in METHOD_ORDER:
            by_iso3 = reference["by_method"][method]
            block = methods[method]
            field_bad = [row["iso3"] for row in block["field"]["values"]
                         if row["iso3"] not in by_iso3
                         or row["score"] != by_iso3[row["iso3"]]["overall"]
                         or float(row["rank"]) != float(by_iso3[row["iso3"]]["rank"])]
            india_ref = by_iso3["IND"]
            india_bad = [
                pillar["id"] for pillar in block["india"]["pillars"]
                if (pillar["score"] != india_ref["pillars"][pillar["id"]]["score"]
                    or float(pillar["rank"]) != float(
                        india_ref["pillars"][pillar["id"]]["rank"]))
            ]
            if block["india"]["score"] != india_ref["overall"] or float(
                    block["india"]["rank"]) != float(india_ref["rank"]):
                india_bad.append("overall")
            top3_bad = [
                row["iso3"] for row in block["field"]["values"][:3]
                if row["score"] != by_iso3[row["iso3"]]["overall"]
                or float(row["rank"]) != float(by_iso3[row["iso3"]]["rank"])
            ]
            checks_ok = checks_ok and not field_bad and not india_bad and not top3_bad
            lines.append(
                f"| `{method}` | "
                + ("all 71 match" if not field_bad else f"MISMATCH {field_bad}")
                + " | "
                + ("all 5 + overall match" if not india_bad
                   else f"MISMATCH {india_bad}")
                + " | "
                + ("match" if not top3_bad else f"MISMATCH {top3_bad}")
                + " |"
            )
        lines += [
            "",
            "## Result",
            "",
            ("Every spot check above matches `chips.json` exactly for both "
             "methods (0 delta on score and rank)." if checks_ok else
             "**SPOT CHECK FAILURES — see the MISMATCH rows above.**"),
            "",
        ]

    lines += [
        "## Notes",
        "",
        "- `field.median`, `.min` and `.max` are computed from that method's 71 "
        "scores; the median of an odd count is an observed score.",
        "- `top15` selects ranks 1-15 within its method; a tie at 15 would carry "
        "the tied rows and show up in `top15MaxRank`.",
        "- Ranks are emitted as integers (`68`, not `68.0`); `chips.json` stores "
        "them as floats. The comparison is numeric.",
        "- `composition` is the top 10 by that method's overall rank.",
        "- `coverage.coverage` is the engine's weight-weighted data coverage; "
        "`indicatorsPresent`/`indicatorsTotal` are the raw leaf counts. Coverage "
        "itself is method-independent, but the score and rank carried beside it "
        "are not.",
        "- No file under `data/SIDE *.csv` is read for writing, and none is "
        "modified. Every number comes from `core/chips.py` through "
        "`core/loader.py`.",
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default=EDITION,
                        help=f"edition to export (default {EDITION})")
    parser.add_argument("--years", nargs="+", default=None,
                        help="override the movement edition window")
    parser.add_argument("--no-report", action="store_true",
                        help="skip the markdown report")
    args = parser.parse_args(argv)

    payload, measurements = build_payload(args.edition, args.years)
    size = write_json(OUT_FILE, payload)
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} ({size} bytes, "
          f"{measurements['countries']} countries, default "
          f"{measurements['defaultMethod']})")
    for method in METHOD_ORDER:
        s = measurements["methods"][method]
        corr = s["correlation"]
        print(f"  {method}: field {s['field']} top15 {s['top15']} "
              f"composition {s['composition']} movement {s['movementCountries']} "
              f"sizeVsScore {s['sizeVsScore']} coverage {s['coverage']}")
        print(f"    India rank {s['india']['rank']} best {s['india']['best']} "
              f"worst {s['india']['worst']}")
        print(f"    corr log10(gdp)~score: pearson {corr['pearson']:.4f} "
              f"spearman {corr['spearman']:.4f} exTop2 {corr['pearsonExTop2']:.4f}"
              f"/{corr['spearmanExTop2']:.4f} (n {corr['n']})")
        print(f"    movement vs series.json: {s['movementSeriesCompared']} compared, "
              f"{len(s['movementSeriesMismatches'])} mismatches; "
              f"composition residual {s['compositionResidual']:.3e}")
        for mismatch in s["movementSeriesMismatches"]:
            print(f"    MISMATCH {method} {mismatch['iso3']} {mismatch['year']}: "
                  f"{mismatch['overview']!r} vs {mismatch['series']!r}")
    print(f"  movement: years {measurements['methods'][METHOD_ORDER[0]]['movementYears']}, "
          f"pool {measurements['methods'][METHOD_ORDER[0]]['movementPool']}")
    print(f"  rank differences between methods: {measurements['rankDiffs']}"
          f"/{measurements['movers']}")
    print(f"  top15 membership changes: {measurements['top15Diffs']}")
    print(f"  GDP join: "
          f"{measurements['methods'][METHOD_ORDER[0]]['gdpJoin']}"
          f"/{measurements['countries']} matched")
    for mover in measurements["worstMovers"]:
        print(f"  mover: {mover['country']:<28} full {mover['rankFull']:>3} "
              f"z {mover['rankZ']:>3} delta {mover['delta']:+}")

    if not args.no_report:
        write_report(REPORT, payload, size, measurements)
        print(f"wrote {REPORT.relative_to(REPO_ROOT)}")
    mismatched = [
        method for method in METHOD_ORDER
        if measurements["methods"][method]["movementSeriesMismatches"]
    ]
    if mismatched:
        print(f"FAIL: movement.scores disagrees with series.json for {mismatched} "
              "(see above)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
