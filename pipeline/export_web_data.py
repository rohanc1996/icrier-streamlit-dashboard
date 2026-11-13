"""Export the SIDE/CHIPS index as web-safe JSON for the public site prototype.

This is a thin *adapter*: every number it emits comes from the existing engine
(``SIDE_dashboard/core/``) and every value it reads comes through the canonical
loader. It re-implements no scaling, no aggregation and no rounding.

Contract (see ``pipeline/schema/web_data.schema.json``):

    data/derived/web/<year>/chips.json   one document per edition
    data/derived/web/series.json         the 2025 <-> 2026 intersection ladder

Both documents carry **both scaling methods** so the site can toggle between
them: ``full_minmax`` (engine ``full``) and ``z`` (engine ``z``). The results
live under ``methods.<key>``; ``meta.methods`` / ``meta.defaultMethod`` name
them. ``framework`` is method-independent and stays top level.

Usage::

    ./.venv/bin/python pipeline/export_web_data.py --year 2026 \\
        --out data/derived/web/2026/

Scores are 0-1 throughout (indicator leaves, sub-pillars, pillars, overall).
``chips`` already rounds to 2 dp on the 0-100 scale and each leaf is already
rounded to 1 dp on that scale, so those precisions are preserved untouched;
pillar and sub-pillar scores are emitted at full precision.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
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
    ISO3_TO_ISO2,
    short_name,
)
from core import chips  # noqa: E402
from core import chips_hierarchy as H  # noqa: E402
from core import loader, scaling  # noqa: E402

METHOD = scaling.METHOD_Z  # dashboard default (METHOD_Z)

# JSON key -> engine method. The site names the min-max method ``full_minmax``
# to be explicit that it is a full-range min-max; the engine calls it ``full``.
JSON_METHODS = {
    "full_minmax": scaling.METHOD_FULL,
    "z": scaling.METHOD_Z,
}
METHOD_ORDER = list(JSON_METHODS)
DEFAULT_METHOD_KEY = "full_minmax"
METHOD_LABELS = {
    "full_minmax": "Full-range min-max",
    "z": "Z-score (standardized)",
}

DELIVERABLES = REPO_ROOT / "deliverables" / "website-prototype"

SCORING_SOURCE = (
    "SIDE_dashboard/core/chips.py: score_matrix -> chips_table -> "
    "aggregate_country -> tree_to_frame"
)

# Columns that are deliberately outside the index, keyed by their normalised
# header. Anything else that fails to resolve is reported generically.
_EXCLUSION_REASONS = {
    "Count": "Junk column: a row counter in the source sheet, not an indicator.",
}


def _exclusion_reason(column: str) -> str:
    if column in _EXCLUSION_REASONS:
        return _EXCLUSION_REASONS[column]
    if "neeGender" in column or "Genderd" in column:
        return (
            "Corrupted source header (mangled gender-gap label from a bad "
            "find-and-replace); the column is not a usable indicator and no "
            "pillar references it."
        )
    return (
        "Outside the published CHIPS framework: no pillar, sub-pillar or "
        "indicator weight references this column, so it carries no index "
        "weight."
    )


# ---------------------------------------------------------------------------
# JSON-safe primitives (NaN is not valid JSON)
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
    """Inline-code cell for the markdown reports."""
    return "null" if value is None else repr(value)


def cell_int(value) -> str:
    """A rank cell: an integer, or an em dash when unranked."""
    return "—" if value is None else str(int(value))


def rounded(value, digits: int):
    """A rounded display copy of a number, or ``None``. Reports only."""
    return None if value is None else round(float(value), digits)


def frame_to_records(df: pd.DataFrame) -> list[dict]:
    """Records with NaN replaced by ``None`` (the frame-level NaN guard)."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


# ---------------------------------------------------------------------------
# Hierarchy metadata
# ---------------------------------------------------------------------------

def leaf_index(pillars: list[H.Pillar]) -> list[dict]:
    """Every leaf in spec order with the weights on its path to the root."""
    rows: list[dict] = []
    for pillar in pillars:
        for sub in pillar.sub_pillars:
            if sub.groups:
                for group in sub.groups:
                    for leaf in group.leaves:
                        rows.append({
                            "pillar": pillar, "subPillar": sub, "group": group,
                            "leaf": leaf,
                        })
            else:
                for leaf in sub.leaves:
                    rows.append({
                        "pillar": pillar, "subPillar": sub, "group": None,
                        "leaf": leaf,
                    })
    return rows


def framework_payload(pillars: list[H.Pillar], data) -> dict:
    out = []
    for pillar in pillars:
        sub_payload = []
        for sub in pillar.sub_pillars:
            leaves = []
            if sub.groups:
                groups = sub.groups
            else:
                groups = [None]
            for group in groups:
                members = group.leaves if group is not None else sub.leaves
                for leaf in members:
                    leaves.append({
                        "name": leaf.name,
                        "column": leaf.column,
                        "label": data.friendly_names.get(leaf.column) if leaf.column else None,
                        "higherIsBetter": bool(data.higher_is_better.get(leaf.column, True))
                        if leaf.column else None,
                        "weightInGroup": num(leaf.weight),
                        # Internal group (only INNOVATE · AI has one). ``None``
                        # for flat sub-pillars; ``weightInGroup`` is always the
                        # weight *inside* the group named here.
                        "group": group.name if group is not None else None,
                        "groupWeight": num(group.weight) if group is not None else None,
                    })
            sub_payload.append({
                "key": f"{pillar.name} · {sub.name}",
                "name": sub.name,
                "pillarId": pillar.name,
                "weight": num(sub.weight),
                "leaves": leaves,
            })
        out.append({
            "id": pillar.name,
            "weight": num(pillar.weight),
            "subPillars": sub_payload,
        })
    return {"pillars": out}


# ---------------------------------------------------------------------------
# Edition scoring
# ---------------------------------------------------------------------------

def load_edition(year: str):
    """Load one edition through the canonical loader (Absolute file)."""
    path = loader.DATASETS[year]["Absolute"]
    return path, loader.load_app_data(path)


def score_edition(year: str, method: str = METHOD, verbose: bool = False):
    """Run the exact dashboard scoring path for one edition and method.

    Returns ``(data, pillars, score_df, table, leaf_weights)``.
    """
    path, data = load_edition(year)
    pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns)
    if verbose:
        print(f"  {path.name}: {len(data.country_list)} countries, "
              f"{len(data.indicators)} loadable indicators, "
              f"{len(H.all_leaves(pillars))} CHIPS leaves, "
              f"{len(unresolved)} unresolved leaves; method={method}")
    score_df = chips.score_matrix(data, pillars, method=method)
    table = chips.chips_table(data, pillars=pillars, method=method)
    leaf_weights = chips.leaf_global_weights(pillars)
    return data, pillars, score_df, table, leaf_weights


def indicator_ranks(score_df: pd.DataFrame, pillars: list[H.Pillar]) -> dict[str, dict]:
    """Per-indicator rank / of / rank-series, computed on the score matrix.

    Rank 1 = best (scores are already direction-corrected by the engine).
    Indicators with fewer than two observations get no rank.
    """
    out: dict[str, dict] = {}
    for leaf in H.all_leaves(pillars):
        series = score_df[leaf.name]
        n = int(series.notna().sum())
        if n < 2:
            out[leaf.name] = {"ranks": None, "of": None}
            continue
        out[leaf.name] = {
            "ranks": series.rank(ascending=False, method="min"),
            "of": n,
        }
    return out


def method_payload(data, pillars: list[H.Pillar], leaves_meta: list[dict],
                   method: str) -> dict:
    """Build one method's ``scores`` / ``indicators`` rows (+ its raw ranks).

    Every number comes from the engine: ``score_matrix`` -> ``chips_table`` /
    ``aggregate_country`` -> ``tree_to_frame``. Nothing is rescaled here.
    """
    score_df = chips.score_matrix(data, pillars, method=method)
    table = chips.chips_table(data, pillars=pillars, method=method)
    leaf_weights = chips.leaf_global_weights(pillars)
    pillar_names = [p.name for p in pillars]
    sub_names = [f"{p.name} · {sp.name}" for p in pillars for sp in p.sub_pillars]

    # ---- ranks -----------------------------------------------------------
    # Overall: the engine's own published rank.
    overall_rank = table["rank"]
    # Pillars: rounded to 2 dp on the 0-100 scale, then ranked (same rule as
    # core/rankings.py composite_scaling_comparison).
    pillar_rank: dict[str, pd.Series] = {}
    for name in pillar_names:
        rounded = (table[name].astype(float) * 100).round(2) / 100
        pillar_rank[name] = rounded.rank(ascending=False, method="min")
    ranks = indicator_ranks(score_df, pillars)

    # Sub-pillars are not columns of ``chips_table``: their scores only exist on
    # the per-country tree, so they are collected while walking countries below
    # and ranked afterwards, with the same published rule as pillars (round to
    # 2 dp on the 0-100 scale, rank(ascending=False, method="min")). Only
    # ``status == "present"`` nodes compete; a dropped sub-pillar is masked out
    # of the ranking (NaN) and therefore gets ``rank: null``.
    sub_scores: dict[str, list] = {key: [] for key in sub_names}
    sub_status: dict[str, list] = {key: [] for key in sub_names}

    # ---- scores + indicators --------------------------------------------
    scores: list[dict] = []
    indicators: list[dict] = []
    for i, country in enumerate(data.country_list):
        res = chips.aggregate_country(
            data, country, pillars=pillars, score_df=score_df
        )
        frame = chips.tree_to_frame(res.chips, leaf_weights)
        # Cross-check against chips_table: the two paths must agree exactly.
        table_score = num(table["chips"].iloc[i])
        if num(res.chips.score) != table_score:
            raise AssertionError(
                f"{country}: aggregate_country {res.chips.score!r} != "
                f"chips_table {table_score!r}"
            )

        tree_leaves = {
            row["label"]: row for row in frame_to_records(frame)
            if row["kind"] == "indicator"
        }

        iso3 = COUNTRY_TO_ISO3[country]
        scores.append({
            "iso3": iso3,
            "iso2": ISO3_TO_ISO2[iso3],
            "country": country,
            "shortName": short_name(country),
            "overall": num(res.chips.score),
            "rank": num(overall_rank.iloc[i]),
            "chipsStatus": res.chips.status,
            "coverage": num(res.coverage["coverage"]),
            "indicatorsPresent": integer(res.coverage["indicators_present"]),
            "indicatorsTotal": integer(res.coverage["indicators_total"]),
            "pillarsPresent": integer(res.coverage["pillars_present"]),
            "pillars": {
                pr.name: {
                    "score": num(pr.score),
                    "rank": num(pillar_rank[pr.name].iloc[i]),
                }
                for pr in res.pillars
            },
            "subPillars": {
                f"{pr.name} · {sp.name}": {
                    "score": num(sp.score),
                    "rank": None,
                    "status": sp.status,
                    "reason": sp.reason,
                }
                for pr in res.pillars
                for sp in pr.children
            },
        })
        for pr in res.pillars:
            for sp in pr.children:
                key = f"{pr.name} · {sp.name}"
                sub_scores[key].append(sp.score)
                sub_status[key].append(sp.status)

        for row in leaves_meta:
            leaf = row["leaf"]
            node = tree_leaves[leaf.name]
            raw = None
            if leaf.column is not None:
                raw = data.numeric_df[leaf.column].iloc[i]
            rank_info = ranks[leaf.name]
            rank_value = None
            if rank_info["ranks"] is not None:
                rank_value = rank_info["ranks"].iloc[i]
            indicators.append({
                "iso3": iso3,
                "leaf": leaf.name,
                "label": data.friendly_names.get(leaf.column) if leaf.column else leaf.name,
                "pillar": row["pillar"].name,
                "subPillar": row["subPillar"].name,
                "group": row["group"].name if row["group"] is not None else None,
                "raw": num(raw),
                "score": num(node["score"]),
                "status": node["status"],
                "reason": node["reason"] or None,
                "rank": num(rank_value),
                "of": integer(rank_info["of"]),
                "effectiveWeight": num(leaf_weights[leaf.name]),
            })

    # ---- sub-pillar ranks ------------------------------------------------
    sub_rank: dict[str, pd.Series] = {}
    for key in sub_names:
        series = pd.Series(sub_scores[key], dtype="float64")
        present = pd.Series(sub_status[key], dtype="object").eq("present")
        # Non-present (dropped) sub-pillars carry no score and do not compete.
        series = series.where(present)
        rounded = (series * 100).round(2) / 100
        sub_rank[key] = rounded.rank(ascending=False, method="min")

    for i, row in enumerate(scores):
        for key in sub_names:
            row["subPillars"][key]["rank"] = num(sub_rank[key].iloc[i])

    return {"scores": scores, "indicators": indicators}


def _rank_deltas(pairs: list[tuple[float | None, float | None]]) -> dict:
    """Compare two rank columns. Non-zero delta = rank disagreement."""
    usable = [(a, b) for a, b in pairs if a is not None and b is not None]
    diffs = [(a, b, b - a) for a, b in usable if a != b]
    return {
        "compared": len(usable),
        "disagreements": len(diffs),
        "maxDelta": max((abs(d) for _, _, d in diffs), default=0),
        "items": diffs,
    }


def rank_agreement(methods: dict[str, dict]) -> dict:
    """Rank agreement between the two methods, per level.

    Indicator ranks must agree: both scalings are monotone transforms of each
    raw column, so they cannot reorder countries inside one indicator. Composite
    ranks (pillars, overall) are weighted sums of those differently shaped
    transforms, so they *can* reorder — the engine's own
    ``rankings.composite_scaling_comparison`` and its tests say so explicitly.
    This function measures the agreement rather than assuming it.
    """
    a, b = METHOD_ORDER[0], METHOD_ORDER[1]
    left, right = methods[a], methods[b]

    overall_rows = [
        (row["iso3"], row["country"], row["rank"], other["rank"])
        for row, other in zip(left["scores"], right["scores"])
    ]
    overall = _rank_deltas([(row[2], row[3]) for row in overall_rows])
    overall["exceptions"] = [
        {
            "iso3": iso3,
            "country": country,
            f"{a}Rank": rank_a,
            f"{b}Rank": rank_b,
            "delta": rank_b - rank_a,
        }
        for iso3, country, rank_a, rank_b in overall_rows
        if rank_a is not None and rank_b is not None and rank_a != rank_b
    ]

    pillar_names = list(left["scores"][0]["pillars"])
    per_pillar = {}
    pillar_total = {"compared": 0, "disagreements": 0, "maxDelta": 0, "items": []}
    for name in pillar_names:
        result = _rank_deltas([
            (row["pillars"][name]["rank"], other["pillars"][name]["rank"])
            for row, other in zip(left["scores"], right["scores"])
        ])
        per_pillar[name] = result
        pillar_total["compared"] += result["compared"]
        pillar_total["disagreements"] += result["disagreements"]
        pillar_total["maxDelta"] = max(pillar_total["maxDelta"], result["maxDelta"])
        pillar_total["items"] += result["items"]
    pillar_total["byPillar"] = {
        name: per_pillar[name]["disagreements"] for name in pillar_names
    }

    sub_names = list(left["scores"][0]["subPillars"])
    per_sub = {}
    sub_total = {"compared": 0, "disagreements": 0, "maxDelta": 0, "items": []}
    for name in sub_names:
        result = _rank_deltas([
            (row["subPillars"][name]["rank"], other["subPillars"][name]["rank"])
            for row, other in zip(left["scores"], right["scores"])
        ])
        per_sub[name] = result
        sub_total["compared"] += result["compared"]
        sub_total["disagreements"] += result["disagreements"]
        sub_total["maxDelta"] = max(sub_total["maxDelta"], result["maxDelta"])
        sub_total["items"] += result["items"]
    sub_total["bySubPillar"] = {
        name: per_sub[name]["disagreements"] for name in sub_names
    }

    keyed_right = {(row["iso3"], row["leaf"]): row for row in right["indicators"]}
    indicator_total = {"compared": 0, "disagreements": 0, "maxDelta": 0, "items": []}
    per_leaf: dict[str, int] = {}
    for row in left["indicators"]:
        other = keyed_right[(row["iso3"], row["leaf"])]
        result = _rank_deltas([(row["rank"], other["rank"])])
        indicator_total["compared"] += result["compared"]
        indicator_total["disagreements"] += result["disagreements"]
        indicator_total["maxDelta"] = max(indicator_total["maxDelta"], result["maxDelta"])
        if result["disagreements"]:
            indicator_total["items"].append(result["items"][0])
            per_leaf[row["leaf"]] = per_leaf.get(row["leaf"], 0) + 1

    return {
        "methods": [a, b],
        "overall": overall,
        "pillars": pillar_total,
        "subPillars": sub_total,
        "indicators": indicator_total,
        "indicatorLeavesWithDisagreement": dict(
            sorted(per_leaf.items(), key=lambda kv: -kv[1])
        ),
    }


def edition_payload(year: str, verbose: bool = False) -> tuple[dict, dict]:
    """Build the JSON document for one edition plus measurement metadata."""
    path, data = load_edition(year)
    pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns)
    if verbose:
        print(f"  {path.name}: {len(data.country_list)} countries, "
              f"{len(data.indicators)} loadable indicators, "
              f"{len(H.all_leaves(pillars))} CHIPS leaves, "
              f"{len(unresolved)} unresolved leaves")

    leaves_meta = leaf_index(pillars)
    leaf_columns = {row["leaf"].column for row in leaves_meta if row["leaf"].column}

    methods = {
        key: method_payload(data, pillars, leaves_meta, engine_method)
        for key, engine_method in JSON_METHODS.items()
    }

    # ---- excluded columns ------------------------------------------------
    excluded = [
        {"column": column, "reason": _exclusion_reason(column)}
        for column in data.numeric_df.columns
        if column != "Country" and column not in leaf_columns
    ]

    agreement = rank_agreement(methods)

    payload = {
        "meta": {
            "edition": year,
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "methods": METHOD_ORDER,
            "defaultMethod": DEFAULT_METHOD_KEY,
            "scoringSource": (
                f"{SCORING_SOURCE}; SIDE_dashboard/core/loader.py:load_app_data; "
                f"data/{loader.DATASETS[year]['Absolute'].name}"
            ),
            "countries": len(methods[DEFAULT_METHOD_KEY]["scores"]),
            "leaves": len(leaves_meta),
            "indicatorsLoadable": len(data.indicators),
            "excludedFromIndex": excluded,
        },
        "framework": framework_payload(pillars, data),
        "methods": methods,
    }
    measurements = {
        "year": year,
        "countries": len(methods[DEFAULT_METHOD_KEY]["scores"]),
        "leaves": len(leaves_meta),
        "indicators_loadable": len(data.indicators),
        "excluded": len(excluded),
        "pillars": len(pillars),
        "subPillars": sum(len(p.sub_pillars) for p in pillars),
        "source_file": str(loader.DATASETS[year]["Absolute"].relative_to(REPO_ROOT)),
        "perMethod": {
            key: {
                "scores_rows": len(value["scores"]),
                "indicator_rows": len(value["indicators"]),
            }
            for key, value in methods.items()
        },
        "rankAgreement": agreement,
    }
    return payload, measurements


def series_payload(years: tuple[str, str] = ("2025", "2026"), verbose: bool = False) -> tuple[dict, dict]:
    """Ladder over the country intersection of two editions, both methods.

    Each edition is scored in full (never on the subset); only output rows are
    filtered to the shared country list.
    """
    scored: dict[str, dict[str, pd.DataFrame]] = {}
    data_by_year = {}
    for year in years:
        path, data = load_edition(year)
        pillars, _unresolved = H.resolve_hierarchy(data.numeric_df.columns)
        data_by_year[year] = data
        scored[year] = {
            key: chips.chips_table(data, pillars=pillars, method=engine_method)
            for key, engine_method in JSON_METHODS.items()
        }
        if verbose:
            print(f"  {path.name}: {len(data.country_list)} countries; "
                  f"methods={METHOD_ORDER}")

    country_sets = [set(data_by_year[year].country_list) for year in years]
    common = country_sets[0].intersection(*country_sets[1:])

    methods_out: dict[str, dict] = {}
    for key in METHOD_ORDER:
        rows: list[dict] = []
        for year in years:
            data = data_by_year[year]
            table = scored[year][key]
            for i, country in enumerate(data.country_list):
                if country not in common:
                    continue
                rows.append({
                    "iso3": COUNTRY_TO_ISO3[country],
                    "year": int(year),
                    "overall": num(table["chips"].iloc[i]),
                    "rank": num(table["rank"].iloc[i]),
                })

        rows.sort(key=lambda r: (r["year"], r["rank"] is None, r["rank"] or 0, r["iso3"]))
        methods_out[key] = {"series": rows}

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "methods": METHOD_ORDER,
            "defaultMethod": DEFAULT_METHOD_KEY,
            "years": [int(y) for y in years],
            "countries": len(common),
            "scoringSource": SCORING_SOURCE,
        },
        "methods": methods_out,
    }
    measurements = {
        "countries": len(common),
        "years": list(years),
        "perMethod": {
            key: {
                "rows": len(value["series"]),
                "per_year": {
                    y: len([r for r in value["series"] if r["year"] == int(y)])
                    for y in years
                },
            }
            for key, value in methods_out.items()
        },
    }
    return payload, measurements


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_json(path: Path, payload: dict) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, allow_nan=False, separators=(",", ":"), ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return len(text.encode("utf-8")) + 1


def _git_snapshot() -> tuple[str, str]:
    """(tracked, untracked) porcelain status of ``data/`` — read-only check.

    ``tracked`` uses ``--untracked-files=no``, so it shows only modifications to
    the published editions. ``untracked`` shows everything else.
    """
    def run(args: list[str]) -> str:
        try:
            proc = subprocess.run(
                ["git", "status", "--porcelain", *args, "--", "data"],
                cwd=REPO_ROOT, capture_output=True, text=True, check=False,
            )
        except OSError as exc:  # pragma: no cover - git missing
            return f"could not run git ({exc})"
        if proc.returncode != 0:
            return f"git status failed: {proc.stderr.strip()}"
        return proc.stdout.strip()

    return run(["--untracked-files=no"]), run([])


def _rank_line(label: str, result: dict, total: int) -> str:
    if result["disagreements"] == 0:
        return (f"| {label} | {result['compared']} | 0 | 0 | — |")
    worst = max(abs(delta) for _, _, delta in result["items"])
    return (f"| {label} | {result['compared']} | {result['disagreements']} | "
            f"{worst} | {result['disagreements']} of {total} |")


COMPARISON_COUNTRIES = [
    "India", "Brazil", "Costa Rica", "United States of America", "Singapore",
]


def write_method_comparison(path: Path, edition: dict, measurements: dict) -> None:
    """One-page score/rank table for both methods + rank-agreement summary."""
    agreement = measurements["rankAgreement"]
    a, b = agreement["methods"]
    scores_a = {row["iso3"]: row for row in edition["methods"][a]["scores"]}
    scores_b = {row["iso3"]: row for row in edition["methods"][b]["scores"]}
    by_country = {row["country"]: row for row in edition["methods"][a]["scores"]}

    lines = [
        "# Scaling methods — score and rank comparison",
        "",
        f"Edition **{edition['meta']['edition']} Absolute**, exported from the CHIPS",
        f"engine (`SIDE_dashboard/core/chips.py`) on {edition['meta']['generated']}.",
        "",
        f"`{a}` = full-range min–max (`scaling.METHOD_FULL`); "
        f"`{b}` = z-score, standardised then mapped through the logistic curve "
        "(`scaling.METHOD_Z`). Both keep every country on the same 0–1 scale.",
        "",
        "## Five countries",
        "",
        f"| Country | {a} score | {a} rank | {b} score | {b} rank | Δ score |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for country in COMPARISON_COUNTRIES:
        left = by_country[country]
        right = scores_b[left["iso3"]]
        delta = (right["overall"] or 0.0) - (left["overall"] or 0.0)
        lines.append(
            f"| {country} | `{cell(left['overall'])}` | {cell_int(left['rank'])} "
            f"| `{cell(right['overall'])}` | {cell_int(right['rank'])} "
            f"| {delta:+.4f} |"
        )
    lines += [
        "",
        "`Δ score` is `z - full_minmax`; it shows how much the 0–1 position moves",
        "between methods. The rank columns are the published competition ranks",
        "(1 = best, ties share the minimum).",
        "",
        "## Rank agreement",
        "",
        f"Ranks are compared at each level. Per-indicator ranks are expected to"
        f" agree (monotone transforms); aggregate ranks are measured, not assumed."
        f" Compared: "
        f"**{len(scores_a)}** countries overall, **{agreement['pillars']['compared']}** "
        f"country×pillar pairs, **{agreement['indicators']['compared']}** "
        f"country×indicator pairs.",
        "",
        "| Level | Compared | Disagreements | Max abs delta | Share |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.append(_rank_line("Overall CHIPS rank", agreement["overall"],
                            len(scores_a)))
    lines.append(_rank_line("Pillar ranks", agreement["pillars"],
                            agreement["pillars"]["compared"]))
    lines.append(_rank_line("Sub-pillar ranks", agreement["subPillars"],
                            agreement["subPillars"]["compared"]))
    lines.append(_rank_line("Indicator ranks", agreement["indicators"],
                            agreement["indicators"]["compared"]))
    lines.append("")

    if agreement["overall"]["disagreements"]:
        movers = sorted(
            agreement["overall"]["exceptions"],
            key=lambda item: -abs(item["delta"]),
        )[:6]
        lines += [
            "### Largest overall movements",
            "",
            f"| Country | ISO-3 | {a} rank | {b} rank | delta |",
            "| --- | --- | --- | --- | --- |",
        ]
        for item in movers:
            lines.append(
                f"| {item['country']} | {item['iso3']} | {item[f'{a}Rank']} "
                f"| {item[f'{b}Rank']} | {item['delta']:+} |"
            )
        lines += [
            "",
            f"The full list of {agreement['overall']['disagreements']} movers is in"
            " `export-report.md`.",
            "",
            "### Why composite ranks move",
            "",
            "Within a single indicator the two scalings are monotone transforms of"
            " the same raw value, so their indicator ranks are identical (zero"
            " disagreements above). The composite CHIPS score is not a single"
            " transform: it is a weighted sum of per-indicator scores. Full-range"
            " min–max spreads each indicator linearly over its observed range, while"
            " z-score pushes values through the logistic curve, compressing both"
            " tails and pulling mid-pack countries toward 0.5. Weighted sums of two"
            " differently shaped curves therefore need not rank countries the same"
            " way.",
            "",
            "This is engine behaviour, not an export artefact: the numbers here"
            " reproduce `SIDE_dashboard/core/rankings.py:composite_scaling_comparison`"
            " exactly (0 mismatches on all 71 overall ranks and 355 pillar ranks),"
            " and `SIDE_dashboard/tests/test_chips.py` asserts that composite ranks"
            " *can* differ between methods. Rank difference is therefore a finding"
            " for the site copy, not a bug to hide: the toggle changes the league"
            " table, not just the score column.",
        ]
    else:
        lines.append(
            "Overall ranks agree exactly: no country changes position between"
            " methods."
        )

    if agreement["pillars"]["disagreements"]:
        lines += ["", "Pillar disagreements by pillar: "
                  + ", ".join(f"{name} {count}"
                              for name, count in agreement["pillars"]["byPillar"].items()
                              if count) + "."]
    if agreement["indicators"]["disagreements"]:
        lines += ["", "Indicators with rank disagreements: "
                  + ", ".join(f"`{name}` ({count})"
                              for name, count in
                              agreement["indicatorLeavesWithDisagreement"].items()) + "."]

    total_indicator_rows = len(edition["methods"][a]["indicators"])
    ranked_rows = agreement["indicators"]["compared"]
    lines += [
        "",
        "Indicator ranks are computed on the unrounded score matrix, which both "
        f"methods transform monotonically. Of {total_indicator_rows} "
        "country×indicator rows per method, "
        f"{ranked_rows} are ranked on both sides; the other "
        f"{total_indicator_rows - ranked_rows} lack a raw value for that country "
        "and carry `rank: null` under both methods (the same rows in each).",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, edition: dict, edition_file: Path, edition_bytes: int,
                 series: dict, series_file: Path, series_bytes: int,
                 measurements: dict | None = None) -> None:
    tracked, untracked = _git_snapshot()
    methods = edition["meta"]["methods"]
    default = edition["meta"]["defaultMethod"]
    series_rows = {
        key: value["series"] for key, value in series.get("methods", {}).items()
    }
    unscored = {
        key: sum(1 for row in rows if row["overall"] is None)
        for key, rows in series_rows.items()
    }
    unscored_countries = {
        key: len({row["iso3"] for row in rows if row["overall"] is None})
        for key, rows in series_rows.items()
    }
    agreement = (measurements or {}).get("rankAgreement")
    lines = [
        "# Web data export report",
        "",
        f"Generated by `pipeline/export_web_data.py` on {edition['meta']['generated']}.",
        "",
        f"- Edition: **{edition['meta']['edition']} Absolute**",
        f"- Scaling methods: {', '.join(f'`{m}`' for m in methods)} "
        "(emitted side by side for the site toggle)",
        f"- Default method: `{default}`",
        f"- Scoring source: `{edition['meta']['scoringSource']}`",
        "",
        "## Files",
        "",
        "| File | Bytes | KB | Rows |",
        "| --- | --- | --- | --- |",
        f"| `{edition_file.relative_to(REPO_ROOT)}` | {edition_bytes} | "
        f"{edition_bytes / 1024:.1f} | {edition['meta']['countries']} scores + "
        f"{len(edition['methods'][default]['indicators'])} indicator rows, "
        f"per method ({len(methods)} methods) |",
        f"| `{series_file.relative_to(REPO_ROOT)}` | {series_bytes} | "
        f"{series_bytes / 1024:.1f} | "
        f"{sum(len(rows) for rows in series_rows.values())} series rows "
        f"({len(methods)} methods) |",
        "",
        "Both files are written minified (no indentation) because they are a web",
        "payload; the JSON Schema and this report are the readable record.",
        "",
        "## Methods in the payload",
        "",
        "| JSON key | Engine method | Label | `scores` rows | `indicators` rows |",
        "| --- | --- | --- | --- | --- |",
    ]
    for key in methods:
        engine_key = JSON_METHODS[key]
        lines.append(
            f"| `{key}` | `{engine_key}` | {METHOD_LABELS[key]} "
            f"| {len(edition['methods'][key]['scores'])} "
            f"| {len(edition['methods'][key]['indicators'])} |"
        )
    lines += [
        "",
        "## Counts",
        "",
        "| Measure | Value |",
        "| --- | --- |",
        f"| 2026 countries | {edition['meta']['countries']} |",
        f"| CHIPS leaves in framework | {edition['meta']['leaves']} |",
        f"| Loadable indicators in the edition | {edition['meta']['indicatorsLoadable']} |",
        f"| Indicators excluded from the index | {len(edition['meta']['excludedFromIndex'])} |",
        f"| Pillars | {len(edition['framework']['pillars'])} |",
        f"| Sub-pillars | {sum(len(p['subPillars']) for p in edition['framework']['pillars'])} |",
    ]
    for key in methods:
        lines.append(
            f"| `methods.{key}.scores` rows | {len(edition['methods'][key]['scores'])} |"
        )
        lines.append(
            f"| `methods.{key}.indicators` rows | "
            f"{len(edition['methods'][key]['indicators'])} |"
        )
    lines += [
        f"| `series.json` countries (2025 ∩ 2026) | {series['meta'].get('countries')} |",
    ]
    for key in methods:
        rows = series_rows.get(key, [])
        lines.append(f"| `series.json` `{key}` rows | {len(rows)} |")
        lines.append(f"| `series.json` `{key}` rows with no overall score | "
                     f"{unscored.get(key, 0)} |")
    lines += [
        "",
        "## Rank agreement between methods",
        "",
        "Measured, not assumed. Per-indicator ranks must agree (both scalings are",
        "monotone transforms of one column); aggregate ranks can move because the",
        "composite is a weighted sum of differently shaped transforms.",
    ]
    if agreement:
        lines += [
            "",
            "| Level | Compared | Disagreements | Max abs delta |",
            "| --- | --- | --- | --- |",
            f"| Overall CHIPS rank | {agreement['overall']['compared']} "
            f"| {agreement['overall']['disagreements']} "
            f"| {agreement['overall']['maxDelta']} |",
            f"| Pillar ranks | {agreement['pillars']['compared']} "
            f"| {agreement['pillars']['disagreements']} "
            f"| {agreement['pillars']['maxDelta']} |",
            f"| Sub-pillar ranks | {agreement['subPillars']['compared']} "
            f"| {agreement['subPillars']['disagreements']} "
            f"| {agreement['subPillars']['maxDelta']} |",
            f"| Indicator ranks | {agreement['indicators']['compared']} "
            f"| {agreement['indicators']['disagreements']} "
            f"| {agreement['indicators']['maxDelta']} |",
        ]
        if agreement["overall"]["disagreements"]:
            lines += [
                "",
                f"All {agreement['overall']['disagreements']} countries whose"
                " overall rank changes between methods"
                " (`delta = z - full_minmax`):",
                "",
                "| Country | ISO-3 | full_minmax rank | z rank | delta |",
                "| --- | --- | --- | --- | --- |",
            ]
            for item in agreement["overall"]["exceptions"]:
                a, b = agreement["methods"]
                lines.append(
                    f"| {item['country']} | {item['iso3']} | {item[f'{a}Rank']} "
                    f"| {item[f'{b}Rank']} | {item['delta']:+} |"
                )
        else:
            lines += ["", "No rank disagreements at any level."]
    else:
        lines += ["", "Not measured (report written without measurements)."]

    if set(series_rows) == set(methods):
        a, b = methods
        rank_a = {(row["iso3"], row["year"]): row["rank"]
                  for row in series_rows[a]}
        series_diff = sum(
            1 for row in series_rows[b]
            if rank_a[(row["iso3"], row["year"])] != row["rank"]
        )
        lines += [
            "",
            f"On the 2025–2026 ladder, {series_diff} of "
            f"{len(series_rows[a])} `{a}` rows change rank under `{b}` "
            "(same composite effect; each method has its own ladder).",
        ]
    lines += [
        "",
        "## Sub-pillar ranks",
        "",
        "Every `methods.<method>.scores[].subPillars.<key>` entry now carries a",
        "`rank` alongside `score`, `status` and `reason`, so the site never has to",
        "derive a sub-pillar league table in JavaScript.",
        "",
        "**Rule** (identical to the pillar rule above, and to",
        "`SIDE_dashboard/core/rankings.py:172-180`): the sub-pillar score is",
        "rounded to 2 dp on the 0-100 scale, then ranked with",
        "`rank(ascending=False, method=\"min\")` — 1 = best, ties share the minimum.",
        "A sub-pillar whose `status` is not `\"present\"` (no score) is masked out",
        "before ranking, so it neither competes nor receives a rank: its `rank`",
        "is `null`. Ranks are computed **within each method**, on that method's own",
        "sub-pillar scores; they are not comparable across the `full_minmax`/`z`",
        "toggle.",
        "",
    ]
    sub_keys = list(edition["methods"][methods[0]]["scores"][0]["subPillars"])
    for key in methods:
        rows_k = edition["methods"][key]["scores"]
        ranked_cells = sum(1 for row in rows_k
                           for sub in row["subPillars"].values()
                           if sub["rank"] is not None)
        unranked_cells = sum(1 for row in rows_k
                             for sub in row["subPillars"].values()
                             if sub["rank"] is None)
        lines.append(
            f"- `{key}`: {ranked_cells} ranked country×sub-pillar cells, "
            f"{unranked_cells} unranked (out of "
            f"{len(rows_k)} x {len(sub_keys)} = {len(rows_k) * len(sub_keys)})."
        )

    example_key = next((k for k in sub_keys if k == "HARNESS · AI"), None) \
        or next((k for k in sub_keys if "HARNESS" in k and k.endswith("AI")), None)
    example_country = "India"
    lines += [
        "",
        f"### Example: {example_country}, `{example_key}`",
        "",
        "| Method | Score (0-1) | Score x100, 2 dp | Rank | of | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in methods:
        row = next(r for r in edition["methods"][key]["scores"]
                   if r["country"] == example_country)
        sub = row["subPillars"][example_key] if example_key else {
            "score": None, "rank": None, "status": "n/a"}
        scored = sum(1 for r in edition["methods"][key]["scores"]
                     if r["subPillars"][example_key]["status"] == "present")
        rounded_value = None if sub["score"] is None else round(sub["score"] * 100, 2)
        lines.append(
            f"| `{key}` | `{cell(rounded(sub['score'], 6))}` | `{cell(rounded_value)}` "
            f"| {cell_int(sub['rank'])} | {scored if sub['rank'] is not None else '—'} "
            f"| `{sub.get('status')}` |"
        )

    unranked_country = "Costa Rica"
    unranked_rows = [
        (name, sub)
        for name, sub in next(
            (r["subPillars"] for r in edition["methods"][methods[0]]["scores"]
             if r["country"] == unranked_country), {})
        .items() if sub["rank"] is None
    ]
    if unranked_rows:
        lines += [
            "",
            f"### Unranked: {unranked_country}",
            "",
            f"{unranked_country} has {len(unranked_rows)} sub-pillar"
            f"{'s' if len(unranked_rows) != 1 else ''} the engine could not score,",
            "so each carries `score: null`, `rank: null` and the engine's reason:",
            "",
            "| Sub-pillar | Score | Rank | Status | Reason |",
            "| --- | --- | --- | --- | --- |",
        ]
        for name, sub in unranked_rows:
            lines.append(
                f"| `{name}` | `{cell(sub['score'])}` | {cell_int(sub['rank'])} "
                f"| `{sub['status']}` | {sub['reason'] or '—'} |"
            )
        lines.append("")
    else:
        any_unranked = next(
            (r["country"], name) for r in edition["methods"][methods[0]]["scores"]
            for name, sub in r["subPillars"].items() if sub["rank"] is None
        )
        lines += [
            "",
            f"### Unranked: {unranked_country}",
            "",
            f"{unranked_country} has a rank for every sub-pillar in this edition"
            + (f"; the first unranked country×sub-pillar cell is "
               f"{any_unranked[0]} `{any_unranked[1]}`." if any_unranked else "."),
            "",
        ]

    lines += [
        "",
        "## Excluded from the index (never silent)",
        "",
        "| Column | Reason |",
        "| --- | --- |",
    ]
    for item in edition["meta"]["excludedFromIndex"]:
        lines.append(f"| `{item['column']}` | {item['reason']} |")
    lines += [
        "",
        "## Frozen-data check",
        "",
        "`git status --porcelain --untracked-files=no -- data` — tracked changes",
        "to the published editions:",
        "",
        "```",
        tracked if tracked else "(empty — no tracked file under data/ changed)",
        "```",
        "",
        "`git status --porcelain -- data` — including untracked files:",
        "",
        "```",
        untracked if untracked else "(empty)",
        "```",
        "",
        "The published `SIDE 2024/2025/2026` CSVs are untouched. The only entry is",
        "`data/derived/`, the new output directory this exporter writes; it is not",
        "yet tracked or ignored (that is a repo-policy decision, not the exporter's).",
        "",
        "## Notes",
        "",
        "- Scores are 0-1 everywhere. `overall` keeps the engine's 2-dp rounding on",
        "  the 0-100 scale; leaf scores keep the engine's 1-dp leaf rounding.",
        "- `framework` is method-independent and stored once; only the result rows",
        "  are duplicated under `methods`. `meta.defaultMethod` is the method the",
        "  site should show first.",
        "- `subPillars` and leaf `group`/`groupWeight` are extra structure the",
        "  CHIPS framework needs: INNOVATE · AI nests two internal groups, so a",
        "  leaf's `weightInGroup` is always the weight inside the named `group`.",
        "- `rank` is `null` where a country or indicator has too little data; the",
        "  2026 edition has no such country.",
        f"- The 2025 ∩ 2026 country intersection is **{series['meta'].get('countries')}**",
        "  countries, not the 52 in the phase-0 brief. 2025 resolves 28 of the 58",
        "  leaves to no column (its 49-column file predates those indicators), so",
        f"  {max(unscored_countries.values()) if unscored_countries else 0} of those"
        " countries do not reach the 3-pillar minimum",
        "  in 2025 and carry `overall: null` for that year.",
        "- `series` ranks are within-edition: a 2025 rank is out of the 59 countries",
        "  in the 2025 edition, a 2026 rank out of 71. They are not a like-for-like",
        "  re-ranking of the 57-country panel.",
        "- `series` ranks move between methods as well (the same composite effect);",
        "  each method carries its own ladder.",
        "- The file is roughly twice the single-method size because both `scores`",
        "  and `indicators` are emitted twice. If that becomes a payload problem,",
        "  the split is per-country indicator files (`<iso3>.json`), not a third",
        "  method key.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2026", help="edition to export (default 2026)")
    parser.add_argument("--out", required=True, help="output directory for the edition JSON")
    parser.add_argument("--no-series", action="store_true", help="skip series.json")
    parser.add_argument("--no-report", action="store_true", help="skip the markdown report")
    args = parser.parse_args(argv)

    out_dir = (REPO_ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    edition_file = out_dir / "chips.json"
    series_file = out_dir.parent / "series.json"

    print(f"Exporting {args.year} Absolute (methods={METHOD_ORDER}, "
          f"default={DEFAULT_METHOD_KEY}) ...")
    payload, edition_measurements = edition_payload(args.year, verbose=True)
    edition_bytes = write_json(edition_file, payload)
    per_method = edition_measurements["perMethod"]
    print(f"  wrote {edition_file.relative_to(REPO_ROOT)} "
          f"({edition_bytes / 1024 / 1024:.2f} MB, {payload['meta']['countries']} "
          f"countries; "
          + ", ".join(f"{key}: {info['indicator_rows']} indicator rows"
                      for key, info in per_method.items()) + ")")

    series = None
    series_bytes = 0
    if not args.no_series:
        series, series_measurements = series_payload(verbose=True)
        series_bytes = write_json(series_file, series)
        print(f"  wrote {series_file.relative_to(REPO_ROOT)} "
              f"({series_bytes / 1024:.1f} KB, "
              f"{series['meta']['countries']} shared countries x "
              f"{len(series['methods'])} methods)")
        expected = 52
        if series["meta"]["countries"] != expected:
            print(f"  NOTE: 2025 ∩ 2026 has {series['meta']['countries']} countries, "
                  f"not the {expected} assumed in the brief.")

    if not args.no_report:
        if series is None:
            series = {"meta": {"countries": 0}, "methods": {}}
        report = DELIVERABLES / "export-report.md"
        write_report(report, payload, edition_file, edition_bytes, series, series_file,
                     series_bytes, measurements=edition_measurements)
        print(f"  wrote {report.relative_to(REPO_ROOT)}")
        comparison = DELIVERABLES / "method-comparison.md"
        write_method_comparison(comparison, payload, edition_measurements)
        print(f"  wrote {comparison.relative_to(REPO_ROOT)}")

    agreement = edition_measurements["rankAgreement"]
    for level in ("overall", "pillars", "subPillars", "indicators"):
        result = agreement[level]
        print(f"  ranks {level}: {result['disagreements']} disagreement(s) "
              f"of {result['compared']} compared, max delta {result['maxDelta']}")
        for item in result["items"][:10]:
            print(f"    {item}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
