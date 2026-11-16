"""Validate ``data/derived/web/overview.json`` (the overview carousel payload).

The payload carries one complete pane set per scaling method under ``methods``
(``z`` and ``full_minmax``), with ``meta`` and the cross-method
``scaleMovement`` at the top level. Checks, in order:

1. The document validates against ``pipeline/schema/overview.schema.json``
   (draft 2020-12), and contains no ``NaN`` / ``Infinity`` token anywhere.
2. ``meta.defaultMethod`` is ``z`` (the deliberate product default), and no
   method block is treated as the default anywhere.
3. Per method block: 71 field values, ranks 1-15 in ``top15``, 10 composition
   rows with five contributions that reproduce that block's composite to
   within 1e-9 once the published 2-dp rounding is applied, 5 India pillars,
   a movement window whose pool is the edition field size, 71 ``sizeVsScore``
   rows with null ``gdpPerCapita`` and GDP > 0, 71 coverage rows in [0, 1],
   and a ``correlation`` block that matches a recomputation of log10(GDP)
   against that method's scores (4 dp).
4. Cross-method invariants: identical country sets, identical movement
   country count, byte-identical ``sizeVsScore.gdp``, the same India pillar
   field sizes, and at least one overall rank difference (the methods are
   expected to disagree; the count is reported).
5. Cross-check against ``data/derived/web/2026/chips.json``: every field score
   and rank, India's five pillar ranks and all ``z`` ranks must match exactly,
   for both methods. Then cross-check each block's ``movement.scores`` against
   that method's ladder in ``data/derived/web/series.json``: exact float
   equality, no tolerance.

Run::

    ./.venv/bin/python pipeline/validate_overview.py
    ./.venv/bin/python pipeline/validate_overview.py --edition 2026
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "pipeline" / "schema" / "overview.schema.json"
WEB_DIR = REPO_ROOT / "data" / "derived" / "web"
OVERVIEW = WEB_DIR / "overview.json"

EXPECTED_COUNTRIES = 71
EXPECTED_METHODS = ["full_minmax", "z"]
DEFAULT_METHOD = "z"
NOMINAL_WEIGHTS = {
    "CONNECT": 0.25,
    "HARNESS": 0.25,
    "INNOVATE": 0.25,
    "PROTECT": 0.125,
    "SUSTAINABILITY": 0.125,
}
COMPOSITION_TOLERANCE = 1e-9
CORRELATION_TOLERANCE = 6e-5  # 4-dp rounding is at most 5e-5
EX_TOP2 = {"USA", "CHN"}


class Failure(Exception):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def _no_non_finite(text: str, label: str) -> None:
    for token in ("NaN", "Infinity", "-Infinity"):
        _assert(token not in text, f"{label}: contains the invalid JSON token {token!r}")


def _walk_numbers(value, path="$"):
    if isinstance(value, float):
        _assert(math.isfinite(value), f"{path}: non-finite number")
    elif isinstance(value, dict):
        for key, item in value.items():
            _walk_numbers(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _walk_numbers(item, f"{path}[{index}]")


# ---------------------------------------------------------------------------
# Correlation recomputation (pure python: log10 x, average ranks, Pearson)
# ---------------------------------------------------------------------------

def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(x, y))
    vx = math.sqrt(sum((a - mx) ** 2 for a in x))
    vy = math.sqrt(sum((b - my) ** 2 for b in y))
    return cov / (vx * vy)


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(values):
        end = index
        while end + 1 < len(values) and values[order[end + 1]] == values[order[index]]:
            end += 1
        average = (index + end) / 2 + 1
        for position in range(index, end + 1):
            ranks[order[position]] = average
        index = end + 1
    return ranks


def _expected_correlation(size_rows: list[dict]) -> dict:
    x = [math.log10(row["gdp"]) for row in size_rows]
    y = [row["score"] for row in size_rows]
    keep = [i for i, row in enumerate(size_rows) if row["iso3"] not in EX_TOP2]
    x2 = [x[i] for i in keep]
    y2 = [y[i] for i in keep]
    return {
        "pearson": round(_pearson(x, y), 4),
        "spearman": round(_pearson(_average_ranks(x), _average_ranks(y)), 4),
        "pearsonExTop2": round(_pearson(x2, y2), 4),
        "spearmanExTop2": round(
            _pearson(_average_ranks(x2), _average_ranks(y2)), 4),
        "n": len(size_rows),
    }


# ---------------------------------------------------------------------------
# Per-method block
# ---------------------------------------------------------------------------

def validate_block(label: str, block: dict, meta: dict, edition: str) -> dict:
    """All structural invariants for one method block. Returns its measurements."""
    prefix = f"methods.{label}"

    # ---- field -----------------------------------------------------------
    field = block["field"]
    values = field["values"]
    _assert(len(values) == EXPECTED_COUNTRIES,
            f"{prefix}.field.values has {len(values)} rows, expected {EXPECTED_COUNTRIES}")
    iso3 = [row["iso3"] for row in values]
    _assert(len(set(iso3)) == len(iso3), f"{prefix}.field.values has duplicate iso3 codes")
    ranks = [row["rank"] for row in values]
    _assert(ranks == sorted(ranks), f"{prefix}.field.values is not sorted by rank")
    _assert(ranks[0] == 1, f"{prefix}: best rank in field.values is {ranks[0]}, expected 1")
    _assert(max(ranks) <= EXPECTED_COUNTRIES,
            f"{prefix}: rank {max(ranks)} exceeds the field")
    scores = [row["score"] for row in values]
    _assert(abs(field["min"] - min(scores)) < 1e-12,
            f"{prefix}.field.min disagrees with the values")
    _assert(abs(field["max"] - max(scores)) < 1e-12,
            f"{prefix}.field.max disagrees with the values")
    ordered = sorted(scores)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    _assert(abs(field["median"] - median) < 1e-12,
            f"{prefix}.field.median disagrees with the values")
    _assert(field["min"] <= field["median"] <= field["max"],
            f"{prefix}: field median outside [min, max]")

    by_iso3 = {row["iso3"]: row for row in values}

    # ---- top15 -----------------------------------------------------------
    top15 = block["top15"]
    _assert(len(top15) >= 15, f"{prefix}.top15 has {len(top15)} rows")
    _assert(max(row["rank"] for row in top15) <= 15,
            f"{prefix}.top15 carries a rank above 15: "
            f"{max(row['rank'] for row in top15)}")
    _assert([row["rank"] for row in top15] == sorted(row["rank"] for row in top15),
            f"{prefix}.top15 is not sorted by rank")
    for row in top15:
        _assert(row == by_iso3[row["iso3"]],
                f"{prefix}.top15 row {row['iso3']} disagrees with field.values")

    # ---- composition -----------------------------------------------------
    composition = block["composition"]
    _assert(len(composition) >= 10, f"{prefix}.composition has {len(composition)} rows")
    _assert([row["rank"] for row in composition] == list(range(1, len(composition) + 1)),
            f"{prefix}.composition is not the top rows in rank order")
    worst_residual = 0.0
    worst_unrounded = 0.0
    for row in composition:
        _assert(row["score"] == by_iso3[row["iso3"]]["score"],
                f"{prefix}.composition / {row['iso3']}: score disagrees with field.values")
        _assert(row["rank"] == by_iso3[row["iso3"]]["rank"],
                f"{prefix}.composition / {row['iso3']}: rank disagrees with field.values")
        ids = [pillar["id"] for pillar in row["pillars"]]
        _assert(ids == list(NOMINAL_WEIGHTS),
                f"{prefix}.composition / {row['iso3']}: pillars {ids}")
        total = 0.0
        for pillar in row["pillars"]:
            weight = NOMINAL_WEIGHTS[pillar["id"]]
            _assert(abs(pillar["weight"] - weight) < 1e-12,
                    f"{prefix}.composition / {row['iso3']} / {pillar['id']}: weight "
                    f"{pillar['weight']} is not the nominal {weight}")
            expected = pillar["score"] * weight
            _assert(abs(pillar["contribution"] - expected) < 1e-12,
                    f"{prefix}.composition / {row['iso3']} / {pillar['id']}: "
                    f"contribution {pillar['contribution']} is not score x weight "
                    f"({expected})")
            total += pillar["contribution"]
        # The published composite is the contribution sum rounded to 2 dp on the
        # 0-100 scale, so the reconstruction must be exact to 1e-9 after that
        # rounding; the raw distance is reported as rounding, not error.
        residual = abs(round(total * 100, 2) / 100 - row["score"])
        worst_residual = max(worst_residual, residual)
        worst_unrounded = max(worst_unrounded, abs(total - row["score"]))
        _assert(residual <= COMPOSITION_TOLERANCE,
                f"{prefix}.composition / {row['iso3']}: contributions sum to "
                f"{total}, published score is {row['score']} "
                f"(rounded-sum residual {residual:.3e})")

    # ---- india -----------------------------------------------------------
    india = block["india"]
    _assert(india["iso3"] == "IND", f"{prefix}: india.iso3 is {india['iso3']!r}")
    _assert(india["score"] == by_iso3["IND"]["score"],
            f"{prefix}: india score disagrees with field.values")
    _assert(india["rank"] == by_iso3["IND"]["rank"],
            f"{prefix}: india rank disagrees with field.values")
    pillar_ids = [pillar["id"] for pillar in india["pillars"]]
    _assert(pillar_ids == list(NOMINAL_WEIGHTS), f"{prefix}: india.pillars ids are {pillar_ids}")
    for pillar in india["pillars"]:
        _assert(pillar["rank"] <= pillar["of"],
                f"{prefix}: india / {pillar['id']}: rank {pillar['rank']} > of {pillar['of']}")
    best = min(india["pillars"], key=lambda p: (p["rank"], pillar_ids.index(p["id"])))
    worst = max(india["pillars"], key=lambda p: (p["rank"], -pillar_ids.index(p["id"])))
    _assert(india["best"] == {"id": best["id"], "rank": best["rank"]},
            f"{prefix}: india.best is {india['best']}, expected {best['id']} {best['rank']}")
    _assert(india["worst"] == {"id": worst["id"], "rank": worst["rank"]},
            f"{prefix}: india.worst is {india['worst']}, expected "
            f"{worst['id']} {worst['rank']}")
    _assert(min(p["rank"] for p in india["pillars"])
            < max(p["rank"] for p in india["pillars"]),
            f"{prefix}: india's best and worst pillar rank are equal")

    # ---- movement --------------------------------------------------------
    movement = block["movement"]
    years = movement["years"]
    year_keys = [str(year) for year in years]
    _assert(len(years) >= 2, f"{prefix}.movement.years has {len(years)} entries")
    _assert(years == sorted(years) and len(set(years)) == len(years),
            f"{prefix}.movement.years is not ascending and unique: {years}")
    _assert(movement["scorableYears"] <= len(years),
            f"{prefix}.movement.scorableYears {movement['scorableYears']} exceeds "
            f"{len(years)} years")
    _assert(len(movement["countries"]) > 0, f"{prefix}.movement.countries is empty")

    pool = movement["pool"]
    _assert(sorted(pool) == sorted(year_keys),
            f"{prefix}.movement.pool keys {sorted(pool)} != years {sorted(year_keys)}")
    for year in year_keys:
        value = pool[year]
        _assert(isinstance(value, int) and not isinstance(value, bool) and value >= 1,
                f"{prefix}.movement.pool[{year}] is {value!r}, expected a positive integer")
        _assert(value <= EXPECTED_COUNTRIES,
                f"{prefix}.movement.pool[{year}] is {value}, above the "
                f"{EXPECTED_COUNTRIES}-country field")
    if str(edition) in pool:
        _assert(pool[str(edition)] == meta["countries"],
                f"{prefix}.movement.pool[{edition}] is {pool[str(edition)]}, "
                f"meta.countries is {meta['countries']}")

    scored_per_year = {year: 0 for year in year_keys}
    for row in movement["countries"]:
        _assert(sorted(row["ranks"]) == sorted(year_keys),
                f"{prefix}.movement / {row['iso3']}: rank keys {sorted(row['ranks'])} "
                f"!= years {year_keys}")
        _assert(sorted(row["scores"]) == sorted(row["ranks"]),
                f"{prefix}.movement / {row['iso3']}: score keys {sorted(row['scores'])} "
                f"!= rank keys {sorted(row['ranks'])}")
        scored = [value for value in row["ranks"].values() if value is not None]
        _assert(len(scored) >= 2,
                f"{prefix}.movement / {row['iso3']}: scored in {len(scored)} editions, "
                "needs >= 2")
        for year in year_keys:
            rank = row["ranks"][year]
            score = row["scores"][year]
            _assert((rank is None) == (score is None),
                    f"{prefix}.movement / {row['iso3']} / {year}: rank {rank!r} and "
                    f"score {score!r} are not both null or both present")
            if rank is not None:
                _assert(1 <= rank <= pool[year],
                        f"{prefix}.movement / {row['iso3']} / {year}: rank {rank} "
                        f"outside 1..{pool[year]}")
            if score is not None:
                _assert(0.0 <= score <= 1.0,
                        f"{prefix}.movement / {row['iso3']} / {year}: score {score} "
                        "outside [0, 1]")
                scored_per_year[year] += 1
    for year in year_keys:
        _assert(scored_per_year[year] <= pool[year],
                f"{prefix}.movement / {year}: {scored_per_year[year]} scored rows "
                f"exceed the pool of {pool[year]}")

    # ---- sizeVsScore -----------------------------------------------------
    size_rows = block["sizeVsScore"]
    _assert(len(size_rows) == EXPECTED_COUNTRIES,
            f"{prefix}.sizeVsScore has {len(size_rows)} rows, expected "
            f"{EXPECTED_COUNTRIES}")
    _assert({row["iso3"] for row in size_rows} == set(iso3),
            f"{prefix}.sizeVsScore does not cover the same countries as field.values")
    for row in size_rows:
        _assert(row["gdpPerCapita"] is None,
                f"{prefix}.sizeVsScore / {row['iso3']}: gdpPerCapita is "
                f"{row['gdpPerCapita']!r}, expected null (no population series)")
        _assert(row["gdp"] > 0,
                f"{prefix}.sizeVsScore / {row['iso3']}: gdp {row['gdp']}")
        _assert(row["score"] == by_iso3[row["iso3"]]["score"],
                f"{prefix}.sizeVsScore / {row['iso3']}: score disagrees with "
                "field.values")
        _assert(row["rank"] == by_iso3[row["iso3"]]["rank"],
                f"{prefix}.sizeVsScore / {row['iso3']}: rank disagrees with "
                "field.values")

    # ---- coverage --------------------------------------------------------
    coverage_rows = block["coverage"]
    _assert(len(coverage_rows) == EXPECTED_COUNTRIES,
            f"{prefix}.coverage has {len(coverage_rows)} rows, expected "
            f"{EXPECTED_COUNTRIES}")
    for row in coverage_rows:
        _assert(0.0 <= row["coverage"] <= 1.0,
                f"{prefix}.coverage / {row['iso3']}: coverage {row['coverage']} "
                "outside [0, 1]")
        _assert(row["indicatorsPresent"] <= row["indicatorsTotal"],
                f"{prefix}.coverage / {row['iso3']}: {row['indicatorsPresent']} "
                f"present of {row['indicatorsTotal']}")
        _assert(row["score"] == by_iso3[row["iso3"]]["score"],
                f"{prefix}.coverage / {row['iso3']}: score disagrees with field.values")

    # ---- correlation -----------------------------------------------------
    correlation = block["correlation"]
    expected = _expected_correlation(size_rows)
    _assert(correlation["n"] == len(size_rows),
            f"{prefix}.correlation.n is {correlation['n']}, expected {len(size_rows)}")
    for key in ("pearson", "spearman", "pearsonExTop2", "spearmanExTop2"):
        _assert(abs(correlation[key] - expected[key]) <= CORRELATION_TOLERANCE,
                f"{prefix}.correlation.{key} is {correlation[key]}, recomputed "
                f"{expected[key]}")

    return {
        "field": len(values),
        "top15": len(top15),
        "composition": len(composition),
        "worstResidual": worst_residual,
        "worstUnrounded": worst_unrounded,
        "movementCountries": len(movement["countries"]),
        "movementYears": years,
        "pool": pool,
        "sizeVsScore": len(size_rows),
        "coverage": len(coverage_rows),
        "india": india,
        "correlation": correlation,
        "byIso3": by_iso3,
        "top15Iso3": {row["iso3"] for row in top15},
    }


def validate_overview(edition: str, schema: dict) -> dict:
    _assert(OVERVIEW.exists(),
            f"missing {OVERVIEW.relative_to(REPO_ROOT)} — run pipeline/export_overview.py")
    text = OVERVIEW.read_text(encoding="utf-8")
    _no_non_finite(text, OVERVIEW.name)
    payload = json.loads(text)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        lines = [f"{len(errors)} schema violation(s) in {OVERVIEW.name}:"]
        for error in errors[:20]:
            location = "/".join(str(p) for p in error.absolute_path) or "<root>"
            lines.append(f"  - {location}: {error.message}")
        raise Failure("\n".join(lines))
    _walk_numbers(payload)

    meta = payload["meta"]
    _assert(meta["edition"] == edition,
            f"meta.edition is {meta['edition']!r}, expected {edition!r}")
    _assert(meta["methods"] == EXPECTED_METHODS,
            f"meta.methods is {meta['methods']}, expected {EXPECTED_METHODS}")
    _assert(meta["defaultMethod"] == DEFAULT_METHOD,
            f"meta.defaultMethod is {meta['defaultMethod']!r}, expected "
            f"{DEFAULT_METHOD!r} (z is the deliberate product default)")
    _assert(meta["countries"] == EXPECTED_COUNTRIES,
            f"meta.countries is {meta['countries']}, expected {EXPECTED_COUNTRIES}")

    methods = payload["methods"]
    _assert(list(methods) == EXPECTED_METHODS,
            f"methods keys are {list(methods)}, expected {EXPECTED_METHODS}")
    stats = {label: validate_block(label, methods[label], meta, edition)
             for label in EXPECTED_METHODS}

    # ---- cross-method invariants ----------------------------------------
    base = EXPECTED_METHODS[0]
    other = EXPECTED_METHODS[1]
    _assert(stats[base]["top15"] == stats[other]["top15"],
            "top15 row counts differ between methods")
    _assert(stats[base]["composition"] == stats[other]["composition"],
            "composition row counts differ between methods")
    _assert(stats[base]["movementCountries"] == stats[other]["movementCountries"],
            f"movement country counts differ: {stats[base]['movementCountries']} vs "
            f"{stats[other]['movementCountries']}")
    _assert(stats[base]["movementYears"] == stats[other]["movementYears"],
            "movement years differ between methods")
    for label in EXPECTED_METHODS:
        _assert(len(stats[label]["india"]["pillars"]) == 5,
                f"methods.{label}.india has {len(stats[label]['india']['pillars'])} "
                "pillars, expected 5")
    _assert(set(stats[base]["byIso3"]) == set(stats[other]["byIso3"]),
            "the two method blocks cover different countries")
    for code in stats[base]["byIso3"]:
        _assert(stats[base]["byIso3"][code]["country"]
                == stats[other]["byIso3"][code]["country"],
                f"methods disagree on the name of {code}")
    pillar_of = {
        label: [p["of"] for p in stats[label]["india"]["pillars"]]
        for label in EXPECTED_METHODS
    }
    _assert(pillar_of[base] == pillar_of[other],
            f"India's pillar field sizes differ between methods: {pillar_of}")

    # GDP is method-independent: identical per country, in both blocks.
    gdp = {
        label: {row["iso3"]: row["gdp"] for row in methods[label]["sizeVsScore"]}
        for label in EXPECTED_METHODS
    }
    _assert(gdp[base] == gdp[other],
            "sizeVsScore.gdp differs between methods; GDP is not method-dependent")

    # The methods are expected to disagree on overall order.
    rank_diffs = sum(
        1 for code in stats[base]["byIso3"]
        if stats[base]["byIso3"][code]["rank"] != stats[other]["byIso3"][code]["rank"]
    )
    _assert(rank_diffs > 0,
            "no country changes overall rank between methods; the methods are "
            "expected to disagree (see SIDE_dashboard/core/rankings.py)")
    top15_diffs = {
        "out": sorted(stats[base]["top15Iso3"] - stats[other]["top15Iso3"]),
        "in": sorted(stats[other]["top15Iso3"] - stats[base]["top15Iso3"]),
    }

    # ---- scaleMovement ---------------------------------------------------
    scale = payload["scaleMovement"]
    _assert(scale["pairs"] == EXPECTED_METHODS, f"scaleMovement.pairs is {scale['pairs']}")
    movers = scale["movers"]
    _assert(len(movers) == EXPECTED_COUNTRIES,
            f"scaleMovement.movers has {len(movers)} rows, expected "
            f"{EXPECTED_COUNTRIES}")
    _assert(len({row["iso3"] for row in movers}) == len(movers),
            "scaleMovement.movers has duplicate iso3 codes")
    for row in movers:
        _assert(row["delta"] == row["rankZ"] - row["rankFull"],
                f"scaleMovement / {row['iso3']}: delta {row['delta']} != "
                f"{row['rankZ']} - {row['rankFull']}")
        _assert(row["rankFull"] == stats["full_minmax"]["byIso3"][row["iso3"]]["rank"],
                f"scaleMovement / {row['iso3']}: rankFull disagrees with "
                "methods.full_minmax.field.values")
        _assert(row["rankZ"] == stats["z"]["byIso3"][row["iso3"]]["rank"],
                f"scaleMovement / {row['iso3']}: rankZ disagrees with "
                "methods.z.field.values")
    deltas = [abs(row["delta"]) for row in movers]
    _assert(deltas == sorted(deltas, reverse=True),
            "scaleMovement.movers is not sorted by absolute delta")
    _assert(sum(1 for row in movers if row["delta"] != 0) == rank_diffs,
            "scaleMovement and the method blocks disagree on how many ranks moved")

    # ---- report ----------------------------------------------------------
    print(f"OK  {OVERVIEW.relative_to(REPO_ROOT)}: default {meta['defaultMethod']}, "
          f"{meta['countries']} countries, methods {EXPECTED_METHODS}")
    for label in EXPECTED_METHODS:
        s = stats[label]
        corr = s["correlation"]
        print(f"    {label}: field {s['field']}, top15 {s['top15']}, "
              f"composition {s['composition']}, movement "
              f"{s['movementCountries']}, sizeVsScore {s['sizeVsScore']}, "
              f"coverage {s['coverage']}")
        print(f"      India rank {s['india']['rank']}, best "
              f"{s['india']['best']['id']} {s['india']['best']['rank']}, worst "
              f"{s['india']['worst']['id']} {s['india']['worst']['rank']}")
        print(f"      composition: 1e-9 residual "
              f"{s['worstResidual']:.3e} (raw rounding distance "
              f"{s['worstUnrounded']:.3e})")
        print(f"      correlation: pearson {corr['pearson']:.4f}, spearman "
              f"{corr['spearman']:.4f}, ex-Top2 {corr['pearsonExTop2']:.4f}/"
              f"{corr['spearmanExTop2']:.4f}, n {corr['n']}")
    print(f"    rank differences between methods: {rank_diffs} of "
          f"{EXPECTED_COUNTRIES}")
    print(f"    top15 membership changes: {len(top15_diffs['out'])} out "
          f"({top15_diffs['out']}), {len(top15_diffs['in'])} in "
          f"({top15_diffs['in']})")
    print(f"    movers {len(movers)}, scaleMovement covers all "
          f"{EXPECTED_COUNTRIES} countries")

    # ---- cross-check against chips.json ----------------------------------
    chips_path = WEB_DIR / edition / "chips.json"
    if chips_path.exists():
        chips = json.loads(chips_path.read_text(encoding="utf-8"))
        for label in EXPECTED_METHODS:
            reference = {row["iso3"]: row
                         for row in chips["methods"][label]["scores"]}
            _assert(set(reference) == set(stats[label]["byIso3"]),
                    f"chips.json[{label}] and overview.json cover different countries")
            mismatches = [
                code for code, row in stats[label]["byIso3"].items()
                if row["score"] != reference[code]["overall"]
                or float(row["rank"]) != float(reference[code]["rank"])
            ]
            _assert(not mismatches,
                    f"methods.{label}.field.values disagrees with chips.json: "
                    f"{mismatches}")
            india_ref = reference["IND"]
            for pillar in stats[label]["india"]["pillars"]:
                ref = india_ref["pillars"][pillar["id"]]
                _assert(pillar["score"] == ref["score"]
                        and float(pillar["rank"]) == float(ref["rank"]),
                        f"methods.{label}.india / {pillar['id']}: "
                        f"{pillar['score']}/{pillar['rank']} != chips.json "
                        f"{ref['score']}/{ref['rank']}")
            _assert(stats[label]["india"]["score"] == india_ref["overall"]
                    and float(stats[label]["india"]["rank"]) == float(india_ref["rank"]),
                    f"methods.{label}.india overall disagrees with chips.json")
            if label == "z":
                for row in movers:
                    _assert(float(row["rankZ"]) == float(reference[row["iso3"]]["rank"]),
                            f"scaleMovement / {row['iso3']}: rankZ {row['rankZ']} != "
                            f"chips.json z rank {reference[row['iso3']]['rank']}")
        print(f"    cross-check: both methods' field scores/ranks, India pillars, "
              f"and all {len(movers)} z ranks match "
              f"{chips_path.relative_to(REPO_ROOT)} exactly")
    else:
        print(f"    NOTE: {chips_path.relative_to(REPO_ROOT)} missing; cross-check skipped")

    # ---- cross-check movement scores against series.json ------------------
    series_path = WEB_DIR / "series.json"
    if series_path.exists():
        ladder = json.loads(series_path.read_text(encoding="utf-8"))
        for label in EXPECTED_METHODS:
            ladder_rows = ladder["methods"][label]["series"]
            series_ref = {(row["iso3"], str(row["year"])): row["overall"]
                          for row in ladder_rows}
            compared = 0
            mismatches = []
            for row in methods[label]["movement"]["countries"]:
                for year in [str(y) for y in stats[label]["movementYears"]]:
                    key = (row["iso3"], year)
                    if key not in series_ref:
                        continue
                    compared += 1
                    if row["scores"][year] != series_ref[key]:
                        mismatches.append((row["iso3"], year,
                                           row["scores"][year], series_ref[key]))
            _assert(compared > 0,
                    f"no {label} movement score could be compared with series.json")
            _assert(not mismatches,
                    f"methods.{label}.movement.scores disagrees with series.json: "
                    f"{mismatches[:5]}")
            print(f"    cross-check: all {compared} {label} movement scores match "
                  f"{series_path.relative_to(REPO_ROOT)} exactly")
    else:
        print(f"    NOTE: {series_path.relative_to(REPO_ROOT)} missing; "
              "movement score cross-check skipped")

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--edition", default="2026", help="edition the payload should carry")
    args = parser.parse_args(argv)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    try:
        validate_overview(args.edition, schema)
    except Failure as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
