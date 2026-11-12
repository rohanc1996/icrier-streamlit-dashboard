#!/usr/bin/env python3
"""Tests for the SIDE 2027 GDP reference and 2027-only ratio derivation.

Run:  python scripts/tests/test_gdp_reference.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import build_gdp_2027 as build  # noqa: E402
import gdp_reference as gdp  # noqa: E402

PASSED = 0
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED
    if condition:
        PASSED += 1
    else:
        FAILURES.append(name)
        print(f"FAIL  {name} {detail}")


def test_reference() -> None:
    reference = gdp.load_gdp_reference()
    check("reference has 71 countries", len(reference) == 71, str(len(reference)))
    check(
        "all years present",
        all(set(record.values) == set(gdp.available_years()) for record in reference.values()),
    )
    check(
        "all GDP values positive",
        all(value > 0 for record in reference.values() for value in record.values.values()),
    )

    absolute_rows = build.read_absolute()
    side_countries = {row["Country"] for row in absolute_rows}
    check("all SIDE countries resolve", side_countries == set(reference))
    check("no unused GDP rows", not (set(reference) - side_countries))

    check(
        "Dominican Republic uses DOM series",
        reference["Dominican Republic"].iso3 == "DOM",
    )
    check(
        "Dominican Republic 2025 GDP",
        gdp.gdp_usd("Dominican Republic", "2025") == 127_407_463_759,
    )

    try:
        gdp.gdp_usd("India", "2026")
    except ValueError:
        check("unsupported year raises", True)
    else:
        check("unsupported year raises", False)

    expected = 100.0 * 1_000_000_000 / gdp.gdp_usd("India", "2025")
    actual = gdp.share_of_gdp(1_000_000_000, "India", "2025")
    check("share_of_gdp computes percent", abs(actual - expected) < 1e-12)


def test_derivation() -> None:
    absolute_rows = build.read_absolute()
    relative_rows = build.read_rows(build.RELATIVE_PATH)
    updated, stats = build.derive_ratio(absolute_rows, relative_rows, build.RATIOS[0])

    check("all 2027 countries computed", stats.computed == 71, str(stats.computed))
    check("no missing numerators", stats.missing_numerator == 0)
    check("no missing GDP", stats.missing_gdp == 0)
    check("no missing countries", stats.missing_country == 0)

    header = relative_rows[0]
    target_index = header.index(build.RATIOS[0].target_column)
    country_index = header.index("Country")
    computed = {
        row[country_index]: row[target_index]
        for row in updated[1:]
    }
    check("Algeria ratio", computed["Algeria"] == "0.68", computed["Algeria"])
    check(
        "Dominican Republic ratio present",
        computed["Dominican Republic"] not in ("", None),
    )

    untouched = True
    for original, changed in zip(relative_rows, updated):
        for index, value in enumerate(original):
            if index != target_index and changed[index] != value:
                untouched = False
    check("only the target column changes", untouched)

    written_rows = build.read_rows(build.RELATIVE_PATH)
    written = {
        row[country_index]: row[target_index]
        for row in written_rows[1:]
    }
    check(
        "2027 Relative file is populated",
        all(value not in ("", None) for value in written.values()),
        str(sum(value in ("", None) for value in written.values())),
    )
    check("2027 Relative file matches derivation", written == computed)


def main() -> int:
    test_reference()
    test_derivation()
    print(f"\n{PASSED} passed, {len(FAILURES)} failed")
    if FAILURES:
        for name in FAILURES:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
