#!/usr/bin/env python3
"""Frozen-edition regression check for SIDE 2024, 2025 and 2026.

Captures each country's CHIPS score, rank, pillar scores and coverage for the
published editions under both scaling methods, then compares against the
checked-in golden files in ``scripts/tests/golden/``.

This is a *change detector*, not a correctness oracle: the golden files record
what the code produced when the baseline was captured. Any movement means a
change to an edition that is supposed to be frozen, and needs a human decision.

Run:

    ./.venv/bin/python scripts/tests/frozen_years.py
    ./.venv/bin/python scripts/tests/frozen_years.py --update
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "SIDE_dashboard"))

from core import chips  # noqa: E402
from core.loader import DATASETS, load_app_data  # noqa: E402

YEARS = ("2024", "2025", "2026")
METHODS = ("full", "z")
GOLDEN = Path(__file__).resolve().parent / "golden"


def snapshot(year: str, method: str) -> list[dict]:
    """Stable, rounded view of one edition under one scaling method."""
    path = DATASETS[year]["Absolute"]
    if not path.exists():
        raise FileNotFoundError(f"Missing dataset for {year}: {path}")

    data = load_app_data(path)
    table = chips.chips_table(data, method=method)

    # to_json handles numpy dtypes and NaN -> null. Rounding to 2 dp keeps the
    # comparison about decisions, not floating-point noise.
    rounded = table.round({c: 2 for c in table.select_dtypes("number").columns})
    return json.loads(rounded.to_json(orient="records"))


def diff(old: list[dict], new: list[dict]) -> list[str]:
    """Short human-readable list of changed rows."""
    old_by_country = {row["Country"]: row for row in old}
    new_by_country = {row["Country"]: row for row in new}
    out: list[str] = []

    for country in sorted(set(old_by_country) | set(new_by_country)):
        before, after = old_by_country.get(country), new_by_country.get(country)
        if before == after:
            continue
        if before is None:
            out.append(f"  + {country}: new row")
            continue
        if after is None:
            out.append(f"  - {country}: row removed")
            continue
        changed = [
            f"{key}: {before.get(key)!r} -> {after.get(key)!r}"
            for key in sorted(set(before) | set(after))
            if before.get(key) != after.get(key)
        ]
        out.append(f"  ~ {country}: " + "; ".join(changed))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="rewrite the golden files from the current code",
    )
    args = parser.parse_args()

    GOLDEN.mkdir(parents=True, exist_ok=True)
    failures = 0

    for year in YEARS:
        for method in METHODS:
            name = f"side_{year}_{method}.json"
            path = GOLDEN / name
            current = snapshot(year, method)

            if args.update:
                path.write_text(
                    json.dumps(current, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print(f"updated {name} ({len(current)} countries)")
                continue

            if not path.exists():
                print(f"MISSING {name} — run with --update to create it")
                failures += 1
                continue

            golden = json.loads(path.read_text(encoding="utf-8"))
            if golden == current:
                print(f"ok      {year} / {method}")
            else:
                failures += 1
                print(f"CHANGED {year} / {method}")
                for line in diff(golden, current)[:40]:
                    print(line)

    if args.update:
        return 0

    if failures:
        print(
            "\nFrozen editions changed. Do not update the baseline until you "
            "have confirmed the movement is intended."
        )
        return 1

    print("\nAll frozen editions unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
