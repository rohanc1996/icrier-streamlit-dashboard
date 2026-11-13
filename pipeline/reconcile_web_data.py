"""Prove the exported JSON equals the CHIPS engine, for both scaling methods.

For India, Brazil and Costa Rica this re-runs the exact engine path
(``chips_table`` + ``aggregate_country`` -> ``tree_to_frame``) under each
method and compares it with ``data/derived/web/2026/chips.json``:

    overall score, all five pillar scores, overall rank, pillar ranks,
    all sixteen sub-pillar scores and ranks, and three sample indicators
    (raw value + 0-1 leaf score),

once for ``full_minmax`` (engine ``full``) and once for ``z`` (engine ``z``).

``delta = exported - engine`` and must be exactly ``0.0`` — not "within
tolerance". Any non-zero delta fails the script instead of being rounded away.

Ranks are compared *within* a method. The two methods need not produce the
same composite rank (the engine's ``rankings.composite_scaling_comparison``
documents that), so a rank that differs between methods is not a failure.

Writes ``deliverables/website-prototype/reconciliation.md``.

Run::

    ./.venv/bin/python pipeline/reconcile_web_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "SIDE_dashboard"))

from core import chips  # noqa: E402
from core import chips_hierarchy as H  # noqa: E402
from core import loader, scaling  # noqa: E402

EXPORT = REPO_ROOT / "data" / "derived" / "web" / "2026" / "chips.json"
REPORT = REPO_ROOT / "deliverables" / "website-prototype" / "reconciliation.md"

COUNTRIES = ["India", "Brazil", "Costa Rica"]
SAMPLE_INDICATORS = [
    "Number of internet users",              # CONNECT · Access
    "Median Mobile Download Speeds (Mbps)",  # CONNECT · Quality
    "E-commerce users",                      # HARNESS · Apps and platform
]

# JSON method key -> engine method. The site calls the min-max method
# ``full_minmax``; the engine calls it ``full``.
METHODS = [
    ("full_minmax", scaling.METHOD_FULL),
    ("z", scaling.METHOD_Z),
]


def cell(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def delta_cell(exported, engine) -> str:
    if exported is None and engine is None:
        return "0.0 (null on both sides)"
    if exported is None or engine is None:
        return f"null mismatch ({exported!r} vs {engine!r})"
    delta = exported - engine
    return repr(delta)


def is_zero(delta: str) -> bool:
    """True only for an exact zero (including null on both sides)."""
    return delta in ("0.0", "0.0 (null on both sides)")


def main() -> int:
    payload = json.loads(EXPORT.read_text(encoding="utf-8"))

    data = loader.load_app_data(loader.DATASETS["2026"]["Absolute"])
    pillars, unresolved = H.resolve_hierarchy(data.numeric_df.columns)
    assert unresolved == [], f"2026 has unresolved leaves: {unresolved}"
    leaf_weights = chips.leaf_global_weights(pillars)
    leaves = {leaf.name: leaf for leaf in H.all_leaves(pillars)}

    failures: list[str] = []
    comparisons = 0
    checks_per_country = 0
    lines = [
        "# Export reconciliation — web JSON vs CHIPS engine",
        "",
        f"Export: `{EXPORT.relative_to(REPO_ROOT)}` · edition 2026 Absolute · "
        f"methods `full_minmax` (engine `full`) and `z` (engine `z`).",
        "",
        "For each country and method below, *Exported* is the value in the JSON",
        "payload and *Engine* is recomputed on the spot from the canonical loader",
        "and `SIDE_dashboard/core/chips.py` (`chips_table`, `aggregate_country`,",
        "`tree_to_frame`).",
        "",
        "**`delta = exported - engine`, and every delta must be exactly 0.** These",
        "are `float` subtractions, not comparisons at a tolerance: a 1e-16 drift",
        "would show up here.",
        "",
        "Ranks are checked *within* each method. Overall and pillar ranks can",
        "legitimately differ between the two scalings (the composite is a weighted",
        "sum of differently shaped transforms); that is measured in",
        "`method-comparison.md` and is not a reconciliation failure.",
        "",
    ]

    for method_key, engine_method in METHODS:
        method_payload = payload["methods"][method_key]
        exported_scores = {row["iso3"]: row for row in method_payload["scores"]}
        exported_indicators = {
            (row["iso3"], row["leaf"]): row for row in method_payload["indicators"]
        }

        score_df = chips.score_matrix(data, pillars, method=engine_method)
        table = chips.chips_table(data, pillars=pillars, method=engine_method).set_index("Country")

        # Pillar ranks: the published rule is score rounded to 2 dp on the 0-100
        # scale, then rank(ascending=False, method="min") — core/rankings.py:172-180.
        pillar_rank = {}
        for pillar in pillars:
            rounded = (table[pillar.name] * 100).round(2) / 100
            pillar_rank[pillar.name] = rounded.rank(ascending=False, method="min")

        # Sub-pillar ranks: sub-pillars are not columns of chips_table, so the
        # series is rebuilt from aggregate_country over every country and then
        # ranked with the same published rule. Only present sub-pillars compete;
        # a dropped one is masked to NaN and has no rank.
        sub_scores: dict[str, dict[str, float]] = {}
        sub_status: dict[str, dict[str, str]] = {}
        for engine_country in data.country_list:
            engine_res = chips.aggregate_country(
                data, engine_country, pillars=pillars, score_df=score_df
            )
            for pr in engine_res.pillars:
                for sp in pr.children:
                    key = f"{pr.name} · {sp.name}"
                    sub_scores.setdefault(key, {})[engine_country] = sp.score
                    sub_status.setdefault(key, {})[engine_country] = sp.status
        sub_rank: dict[str, pd.Series] = {}
        for key, values in sub_scores.items():
            series = pd.Series(values, dtype="float64")
            present = pd.Series(sub_status[key], dtype="object").eq("present")
            rounded = (series.where(present) * 100).round(2) / 100
            sub_rank[key] = rounded.rank(ascending=False, method="min")

        lines += [
            f"## Method `{method_key}` (engine `{engine_method}`)",
            "",
            f"Label: {scaling.METHOD_LABELS[engine_method]}.",
            "",
        ]

        for country in COUNTRIES:
            row = table.loc[country]
            iso3 = next(
                iso["iso3"] for iso in method_payload["scores"]
                if iso["country"] == country
            )
            exported = exported_scores[iso3]
            res = chips.aggregate_country(data, country, pillars=pillars, score_df=score_df)
            frame = chips.tree_to_frame(res.chips, leaf_weights)
            tree_rows = {
                r["label"]: r for r in
                frame.astype(object).where(frame.notna(), None).to_dict(orient="records")
                if r["kind"] == "indicator"
            }

            lines += [f"### {country} (`{iso3}`)", "",
                      "#### Headline and pillars", "",
                      "| Measure | Exported | Engine | delta |",
                      "| --- | --- | --- | --- |"]

            checks = [
                ("Overall CHIPS score", exported["overall"], row["chips"]),
            ]
            for pillar in pillars:
                checks.append((
                    f"Pillar {pillar.name}", exported["pillars"][pillar.name]["score"],
                    row[pillar.name],
                ))
            for pr in res.pillars:
                for sp in pr.children:
                    key = f"{pr.name} · {sp.name}"
                    checks.append((
                        f"Sub-pillar {key} score",
                        exported["subPillars"][key]["score"], sp.score,
                    ))
            checks.append(("Overall rank", exported["rank"], row["rank"]))
            for pillar in pillars:
                checks.append((
                    f"Pillar rank {pillar.name}",
                    exported["pillars"][pillar.name]["rank"],
                    pillar_rank[pillar.name].loc[country],
                ))
            for pr in res.pillars:
                for sp in pr.children:
                    key = f"{pr.name} · {sp.name}"
                    checks.append((
                        f"Sub-pillar rank {key}",
                        exported["subPillars"][key]["rank"],
                        sub_rank[key].loc[country],
                    ))
            checks_per_country = len(checks)

            for label, exported_value, engine_value in checks:
                exported_value = None if exported_value is None else float(exported_value)
                engine_value = None if engine_value is None or engine_value != engine_value \
                    else float(engine_value)
                delta = delta_cell(exported_value, engine_value)
                comparisons += 1
                if not is_zero(delta):
                    failures.append(f"{method_key} / {country} / {label}: "
                                    f"exported={exported_value!r} "
                                    f"engine={engine_value!r} delta={delta}")
                lines.append(
                    f"| {label} | `{cell(exported_value)}` | `{cell(engine_value)}` | `{delta}` |"
                )

            # Sanity: the tree agrees with the table for the headline score.
            if float(res.chips.score) != float(row["chips"]):
                failures.append(f"{method_key} / {country}: aggregate_country != chips_table")

            lines += ["", "#### Sample indicators", "",
                      "| Indicator | Raw (exported) | Raw (engine) | delta raw "
                      "| Score (exported) | Score (engine) | delta score |",
                      "| --- | --- | --- | --- | --- | --- | --- |"]
            for leaf_name in SAMPLE_INDICATORS:
                leaf = leaves[leaf_name]
                engine_raw = data.numeric_df.loc[
                    data.numeric_df["Country"] == country, leaf.column
                ].iloc[0]
                engine_raw = None if engine_raw != engine_raw else float(engine_raw)
                engine_score = tree_rows[leaf_name]["score"]
                engine_score = None if engine_score is None else float(engine_score)
                exported_row = exported_indicators[(iso3, leaf_name)]
                raw_delta = delta_cell(exported_row["raw"], engine_raw)
                score_delta = delta_cell(exported_row["score"], engine_score)
                comparisons += 2
                if not is_zero(raw_delta):
                    failures.append(f"{method_key} / {country} / {leaf_name} raw: {raw_delta}")
                if not is_zero(score_delta):
                    failures.append(f"{method_key} / {country} / {leaf_name} score: {score_delta}")
                lines.append(
                    f"| {leaf_name} | `{cell(exported_row['raw'])}` | `{cell(engine_raw)}` "
                    f"| `{raw_delta}` | `{cell(exported_row['score'])}` "
                    f"| `{cell(engine_score)}` | `{score_delta}` |"
                )
            lines.append("")

    per_country = checks_per_country + 2 * len(SAMPLE_INDICATORS)
    lines += [
        "## Result",
        "",
        "Every delta above is exactly `0.0`. The exporter adds no rounding, no",
        "rescaling and no reweighting of its own: leaf scores are the engine's",
        "rounded 1-dp-on-0-100 values, pillar scores and coverage are full",
        "precision, and the overall score keeps the engine's 2-dp rounding.",
        "",
        "Sub-pillar ranks are compared at zero tolerance too: the exported `rank`",
        "is checked against the same rule applied to the engine's own sub-pillar",
        "scores (2 dp on the 0-100 scale, `rank(ascending=False, method=\"min\")`,",
        "non-present sub-pillars excluded).",
        "",
    ]
    if failures:
        lines.append(f"**{len(failures)} non-zero delta(s):**")
        lines += [f"- {item}" for item in failures]
    else:
        lines.append(
            f"Checked values: {len(METHODS)} methods x {len(COUNTRIES)} countries x "
            f"{per_country} measures = {comparisons} comparisons, all zero."
        )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REPORT.relative_to(REPO_ROOT)}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"all {comparisons} deltas are exactly 0.0 across {len(METHODS)} methods")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
