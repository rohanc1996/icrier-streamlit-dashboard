#!/usr/bin/env python3
"""Derive GDP-denominated indicators for SIDE 2027 only.

Reads ``data/SIDE 2027 - Absolute.csv``, computes the registered ratios and
writes them into ``data/SIDE 2027 - Relative.csv``.  No other edition is read
or written.

Run:  python scripts/build_gdp_2027.py --dry-run
      python scripts/build_gdp_2027.py
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from gdp_reference import available_years, load_gdp_reference, share_of_gdp

ROOT = Path(__file__).resolve().parents[1]
ABSOLUTE_PATH = ROOT / "data" / "SIDE 2027 - Absolute.csv"
RELATIVE_PATH = ROOT / "data" / "SIDE 2027 - Relative.csv"
EDITION_YEAR = "2027"


@dataclass(frozen=True)
class RatioSpec:
    target_column: str
    numerator_column: str
    indicator_year: str
    numerator_to_usd: float = 1_000_000.0


RATIOS: tuple[RatioSpec, ...] = (
    RatioSpec(
        target_column="Total digitally delivered services (million USD) as percent of GDP USD",
        numerator_column="Digitally delivered services (exports)",
        indicator_year="2025",
    ),
)


@dataclass
class DerivationStats:
    computed: int = 0
    missing_numerator: int = 0
    missing_gdp: int = 0
    missing_country: int = 0


def _parse_number(text: str | None) -> float | None:
    if text is None:
        return None
    cleaned = str(text).strip().replace(",", "")
    if not cleaned:
        return None
    return float(cleaned)


def read_rows(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle))


def read_absolute(path: Path = ABSOLUTE_PATH) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def derive_ratio(
    absolute_rows: list[dict[str, str]],
    relative_rows: list[list[str]],
    spec: RatioSpec,
) -> tuple[list[list[str]], DerivationStats]:
    """Return a copy of ``relative_rows`` with one GDP ratio filled in."""
    if not relative_rows:
        raise ValueError("Relative file is empty")

    header = relative_rows[0]
    column_index = header.index(spec.target_column)
    country_index = header.index("Country")
    absolute_by_country = {row["Country"]: row for row in absolute_rows}

    updated = [list(row) for row in relative_rows]
    stats = DerivationStats()

    for row in updated[1:]:
        if len(row) < len(header):
            row.extend([""] * (len(header) - len(row)))
        country = row[country_index].strip()
        absolute_row = absolute_by_country.get(country)
        if absolute_row is None:
            stats.missing_country += 1
            row[column_index] = ""
            continue

        numerator = _parse_number(absolute_row.get(spec.numerator_column))
        if numerator is None:
            stats.missing_numerator += 1
            row[column_index] = ""
            continue

        value = share_of_gdp(
            numerator * spec.numerator_to_usd,
            country,
            spec.indicator_year,
            as_percent=True,
        )
        if value is None:
            stats.missing_gdp += 1
            row[column_index] = ""
            continue

        row[column_index] = f"{value:.2f}"
        stats.computed += 1

    return updated, stats


def write_rows(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Compute without writing")
    args = parser.parse_args()

    if EDITION_YEAR not in ABSOLUTE_PATH.name or EDITION_YEAR not in RELATIVE_PATH.name:
        raise RuntimeError("This builder is restricted to the 2027 edition")

    absolute_rows = read_absolute()
    relative_rows = read_rows(RELATIVE_PATH)

    side_countries = [row["Country"] for row in absolute_rows]
    reference = load_gdp_reference()
    missing = [country for country in side_countries if country not in reference]
    unused = [country for country in reference if country not in set(side_countries)]

    print(f"GDP reference: {len(reference)} countries, years {', '.join(available_years())}")
    if missing:
        print(f"Missing GDP for: {', '.join(missing)}")
    if unused:
        print(f"Unused GDP rows: {', '.join(unused)}")

    updated = relative_rows
    for spec in RATIOS:
        updated, stats = derive_ratio(absolute_rows, updated, spec)
        print(f"\n{spec.target_column}")
        print(f"  numerator: {spec.numerator_column} ({spec.indicator_year})")
        print(f"  computed: {stats.computed}")
        print(f"  missing numerator: {stats.missing_numerator}")
        print(f"  missing GDP: {stats.missing_gdp}")
        print(f"  missing country: {stats.missing_country}")

    if args.dry_run:
        print("\nDry run: no files written")
        return 0

    write_rows(RELATIVE_PATH, updated)
    print(f"\nWrote {RELATIVE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
