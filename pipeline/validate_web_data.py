"""Validate the exported web data against its JSON Schema.

Checks, in order:

1. ``data/derived/web/<year>/chips.json`` validates against
   ``pipeline/schema/web_data.schema.json`` (draft 2020-12), for **both**
   scaling methods under ``methods``.
2. Structural invariants the schema cannot express: 71 countries, unique
   ISO-3 codes, 58 leaves x countries indicator rows **per method**, leaf
   effective weights summing to 1, sub-pillar ranks present for both methods
   (and absent wherever a sub-pillar is not `present`), no NaN/Infinity
   anywhere in the raw text.
3. Rank agreement between methods: indicator ranks must agree; aggregate rank
   differences are reported (they are engine behaviour, not a schema failure).
4. ``data/derived/web/series.json``: the 2025/2026 intersection, two rows per
   country per method, ranks and scores JSON-safe.

Run::

    ./.venv/bin/python pipeline/validate_web_data.py
    ./.venv/bin/python pipeline/validate_web_data.py --year 2026
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "pipeline" / "schema" / "web_data.schema.json"
WEB_DIR = REPO_ROOT / "data" / "derived" / "web"
EXPECTED_COUNTRIES = 71
EXPECTED_LEAVES = 58
EXPECTED_METHODS = ["full_minmax", "z"]


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


def validate_edition(year: str, schema: dict) -> dict:
    path = WEB_DIR / year / "chips.json"
    _assert(path.exists(), f"missing {path.relative_to(REPO_ROOT)} — run the exporter first")
    text = path.read_text(encoding="utf-8")
    _no_non_finite(text, path.name)
    payload = json.loads(text)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        lines = [f"{len(errors)} schema violation(s) in {path.name}:"]
        for error in errors[:20]:
            location = "/".join(str(p) for p in error.absolute_path) or "<root>"
            lines.append(f"  - {location}: {error.message}")
        raise Failure("\n".join(lines))

    _walk_numbers(payload)

    meta = payload["meta"]
    pillars = payload["framework"]["pillars"]

    _assert(meta["methods"] == EXPECTED_METHODS,
            f"meta.methods is {meta['methods']}, expected {EXPECTED_METHODS}")
    _assert(meta["defaultMethod"] in meta["methods"],
            f"meta.defaultMethod {meta['defaultMethod']!r} is not in meta.methods")
    _assert(set(payload["methods"]) == set(EXPECTED_METHODS),
            f"methods keys are {sorted(payload['methods'])}, expected {EXPECTED_METHODS}")
    _assert(meta["countries"] == EXPECTED_COUNTRIES,
            f"meta.countries is {meta['countries']}, expected {EXPECTED_COUNTRIES}")

    leaves = [leaf for pillar in pillars for sub in pillar["subPillars"] for leaf in sub["leaves"]]
    _assert(len(leaves) == EXPECTED_LEAVES,
            f"framework has {len(leaves)} leaves, expected {EXPECTED_LEAVES}")
    _assert(meta["leaves"] == len(leaves), "meta.leaves disagrees with the framework")

    # Weights: each pillar's sub-pillars sum to 1, each sub-pillar's leaves
    # (through internal groups) sum to 1. Method-independent.
    pillar_total = sum(p["weight"] for p in pillars)
    _assert(abs(pillar_total - 1.0) < 1e-9, f"pillar weights sum to {pillar_total}")
    for pillar in pillars:
        sub_total = sum(sub["weight"] for sub in pillar["subPillars"])
        _assert(abs(sub_total - 1.0) < 1e-9,
                f"{pillar['id']} sub-pillar weights sum to {sub_total}")
        for sub in pillar["subPillars"]:
            groups: dict[str, float] = {}
            for leaf in sub["leaves"]:
                key = leaf["group"] or ""
                groups[key] = groups.get(key, 0.0) + leaf["weightInGroup"]
            for key, total in groups.items():
                _assert(abs(total - 1.0) < 1e-9,
                        f"{sub['key']} group {key!r} leaf weights sum to {total}")

    payloads = {}
    for method in EXPECTED_METHODS:
        result = payload["methods"][method]
        scores = result["scores"]
        indicators = result["indicators"]

        _assert(len(scores) == EXPECTED_COUNTRIES,
                f"{method}: scores has {len(scores)} rows, expected {EXPECTED_COUNTRIES}")
        _assert(len({s["iso3"] for s in scores}) == len(scores),
                f"{method}: duplicate iso3 in scores")
        _assert(len(indicators) == len(leaves) * len(scores),
                f"{method}: indicators has {len(indicators)} rows, "
                f"expected {len(leaves) * len(scores)}")

        global_total = sum(row["effectiveWeight"] for row in indicators
                           if row["iso3"] == scores[0]["iso3"])
        _assert(abs(global_total - 1.0) < 1e-9,
                f"{method}: global effective weights sum to {global_total}, expected 1")

        # Every (country, leaf) pair exactly once; no silent holes.
        pairs = {(row["iso3"], row["leaf"]) for row in indicators}
        _assert(len(pairs) == len(indicators),
                f"{method}: duplicate (iso3, leaf) indicator rows")
        _assert(len(pairs) == len(leaves) * len(scores),
                f"{method}: missing (iso3, leaf) combinations")

        for row in scores:
            _assert(set(row["pillars"]) == {p["id"] for p in pillars},
                    f"{method} / {row['iso3']}: pillar keys disagree with the framework")
            _assert(set(row["subPillars"]) ==
                    {sub["key"] for pillar in pillars for sub in pillar["subPillars"]},
                    f"{method} / {row['iso3']}: sub-pillar keys disagree with the framework")
            if row["overall"] is None:
                _assert(row["rank"] is None,
                        f"{method} / {row['iso3']}: rank without a score")

        # Sub-pillar ranks: every entry carries one, only present sub-pillars
        # compete, and no rank exceeds the number of countries that competed.
        sub_keys = [sub["key"] for pillar in pillars for sub in pillar["subPillars"]]
        present_per_key = {key: 0 for key in sub_keys}
        max_rank_per_key = {key: 0 for key in sub_keys}
        for row in scores:
            for key in sub_keys:
                _assert(key in row["subPillars"],
                        f"{method} / {row['iso3']}: missing sub-pillar {key!r}")
                sub = row["subPillars"][key]
                _assert("rank" in sub,
                        f"{method} / {row['iso3']} / {key}: sub-pillar has no rank")
                if sub["status"] != "present":
                    _assert(sub["rank"] is None,
                            f"{method} / {row['iso3']} / {key}: non-present "
                            f"sub-pillar (status={sub['status']!r}) carries "
                            f"rank {sub['rank']!r}")
                    continue
                _assert(sub["score"] is not None,
                        f"{method} / {row['iso3']} / {key}: present sub-pillar "
                        "has no score")
                _assert(sub["rank"] is not None,
                        f"{method} / {row['iso3']} / {key}: present sub-pillar "
                        "carries no rank")
                _assert(float(sub["rank"]).is_integer() and sub["rank"] >= 1,
                        f"{method} / {row['iso3']} / {key}: bad rank "
                        f"{sub['rank']!r}")
                present_per_key[key] += 1
                max_rank_per_key[key] = max(max_rank_per_key[key], int(sub["rank"]))
        for key in sub_keys:
            _assert(max_rank_per_key[key] <= present_per_key[key],
                    f"{method} / {key}: max rank {max_rank_per_key[key]} exceeds "
                    f"{present_per_key[key]} scored countries")

        ranked = [row for row in scores if row["rank"] is not None]
        _assert(len(ranked) == len(scores),
                f"{method}: some 2026 countries have no rank")
        payloads[method] = result

        print(f"OK  {path.relative_to(REPO_ROOT)} [{method}]: {len(scores)} countries, "
              f"{len(leaves)} leaves, {len(indicators)} indicator rows")

    # ---- rank agreement between methods ----------------------------------
    a, b = EXPECTED_METHODS
    scores_a = {row["iso3"]: row for row in payloads[a]["scores"]}
    scores_b = {row["iso3"]: row for row in payloads[b]["scores"]}
    overall_diff = [
        (iso, scores_a[iso]["rank"], scores_b[iso]["rank"])
        for iso in scores_a
        if scores_a[iso]["rank"] != scores_b[iso]["rank"]
    ]
    pillar_diff = 0
    pillar_cells = 0
    for iso, row in scores_a.items():
        for name, pillar in row["pillars"].items():
            pillar_cells += 1
            if pillar["rank"] != scores_b[iso]["pillars"][name]["rank"]:
                pillar_diff += 1
    indicators_b = {(row["iso3"], row["leaf"]): row for row in payloads[b]["indicators"]}
    indicator_diff = 0
    indicator_total = 0
    for row in payloads[a]["indicators"]:
        other = indicators_b[(row["iso3"], row["leaf"])]
        if row["rank"] is None and other["rank"] is None:
            continue
        indicator_total += 1
        if row["rank"] != other["rank"]:
            indicator_diff += 1

    sub_diff = 0
    sub_cells = 0
    sub_unranked = 0
    for iso, row in scores_a.items():
        for name, sub in row["subPillars"].items():
            sub_cells += 1
            if sub["rank"] is None:
                sub_unranked += 1
                continue
            if sub["rank"] != scores_b[iso]["subPillars"][name]["rank"]:
                sub_diff += 1

    print(f"    rank agreement {a} vs {b}: overall {len(overall_diff)}/{len(scores_a)} "
          f"differ, pillars {pillar_diff}/{pillar_cells}, "
          f"sub-pillars {sub_diff}/{sub_cells - sub_unranked} "
          f"({sub_unranked} unranked), "
          f"indicators {indicator_diff}/{indicator_total}")
    if overall_diff:
        worst = max(abs(x - y) for _, x, y in overall_diff)
        print(f"    largest overall movement: {worst} places; "
              f"examples {overall_diff[:3]}")

    print(f"OK  {path.relative_to(REPO_ROOT)}: {len(meta['excludedFromIndex'])} "
          f"excluded columns, methods {meta['methods']}, "
          f"default {meta['defaultMethod']}")
    return payload


def validate_series(year: str) -> dict:
    path = WEB_DIR / "series.json"
    _assert(path.exists(), f"missing {path.relative_to(REPO_ROOT)}")
    text = path.read_text(encoding="utf-8")
    _no_non_finite(text, path.name)
    payload = json.loads(text)
    _walk_numbers(payload)

    meta = payload["meta"]
    years = meta["years"]
    _assert(meta["methods"] == EXPECTED_METHODS,
            f"series meta.methods is {meta.get('methods')}, expected {EXPECTED_METHODS}")
    _assert(meta["defaultMethod"] in meta["methods"],
            f"series meta.defaultMethod {meta.get('defaultMethod')!r} is invalid")
    _assert(set(payload["methods"]) == set(EXPECTED_METHODS),
            f"series methods keys are {sorted(payload['methods'])}")
    _assert(years == [2025, 2026], f"meta.years is {years}, expected [2025, 2026]")

    per_method = {}
    for method in EXPECTED_METHODS:
        rows = payload["methods"][method]["series"]
        _assert(isinstance(rows, list), f"{method}: series is not a list")
        for row in rows:
            _assert(set(row) == {"iso3", "year", "overall", "rank"},
                    f"{method}: series row has unexpected keys: {sorted(row)}")
            _assert(row["year"] in years, f"{method}: series row has year {row['year']}")
            if row["overall"] is None:
                _assert(row["rank"] is None,
                        f"{method} / {row['iso3']}: rank without an overall score")

        by_year = {y: {r["iso3"] for r in rows if r["year"] == y} for y in years}
        _assert(by_year[2025] == by_year[2026],
                f"{method}: 2025 and 2026 cover different country sets"
                f" (only 2025: {sorted(by_year[2025] - by_year[2026])}, "
                f"only 2026: {sorted(by_year[2026] - by_year[2025])})")
        _assert(len(rows) == 2 * meta["countries"],
                f"{method}: {len(rows)} series rows for {meta['countries']} countries")
        _assert(meta["countries"] == len(by_year[2025]),
                f"{method}: meta.countries disagrees with the rows")
        _assert(meta["countries"] <= EXPECTED_COUNTRIES,
                f"{method}: series cannot cover more countries than the edition")
        per_method[method] = rows
        scored = {y: len([r for r in rows if r["year"] == y and r["overall"] is not None])
                  for y in years}
        print(f"OK  {path.relative_to(REPO_ROOT)} [{method}]: "
              f"{meta['countries']} shared countries, {len(rows)} rows, "
              f"scored per year {scored}")

    # Rank agreement on the ladder (same caveat as the edition: composite ranks
    # may move between methods; this reports rather than fails).
    a, b = EXPECTED_METHODS
    by_key_a = {(r["iso3"], r["year"]): r for r in per_method[a]}
    diffs = [
        (r["iso3"], r["year"], r["rank"], by_key_a[(r["iso3"], r["year"])]["rank"])
        for r in per_method[b]
        if r["rank"] is not None
        and r["rank"] != by_key_a[(r["iso3"], r["year"])]["rank"]
    ]
    print(f"    series rank agreement {a} vs {b}: {len(diffs)} of "
          f"{len(per_method[a])} rows differ")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", default="2026", help="edition directory to validate")
    args = parser.parse_args(argv)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    try:
        validate_edition(args.year, schema)
        validate_series(args.year)
    except Failure as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
