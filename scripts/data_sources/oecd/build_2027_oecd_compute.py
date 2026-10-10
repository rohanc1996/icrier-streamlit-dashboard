#!/usr/bin/env python3
"""Add the OECD "GPU availability by AI capability" indicator to the 2027 SIDE
base files.

Indicator (CONNECT, not yet part of the scored CHIPS hierarchy)
---------------------------------------------------------------
The indicator is the count of availability zones hosting high (Tier 1) AI
capability GPUs, which the two-dataset design expresses in its two variants:

  * Absolute (``data/SIDE 2027 - Absolute.csv``):
      ``Availability zones hosting high AI capability (Tier 1) GPUs``
      = ``az_has_training_gpu`` on the ``Count of AZs`` rows.
  * Relative (``data/SIDE 2027 - Relative.csv``):
      ``% of availability zones hosting high AI capability (Tier 1) GPUs``
      = the same field on the ``Percentage of total AZs`` rows.

Tier 1 GPUs are those capable of AI training, fine-tuning and inference
(the "high AI capability" band of the OECD chart).  Higher is better.  The
Relative file carries the *published* OECD percentage (an integer); the OECD
computes each band by truncating, so a country's five bands can sum to 97-100.

``loader.RELATIVE_TO_CANONICAL`` maps the Relative header back to the Absolute
one, so the dashboard treats count (Absolute) and share (Relative) as the two
variants of a single indicator.

Country mapping
---------------
The OECD table keys on ISO-3 codes; SIDE keys on canonical country names.
``SIDE_dashboard/components/country_names.py`` is the single source of truth
for that mapping, so it is imported rather than duplicated.  Codes with no SIDE
row (Bahrain, Taiwan, Hong Kong) and the ``ALL`` aggregate are dropped.  The
remaining 33 SIDE countries are written as empty cells (the file's existing
missing-value convention).

The column is appended to each file (idempotently: a re-run replaces it) so no
existing column or row is disturbed.

Run:  python scripts/data_sources/oecd/build_2027_oecd_compute.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from SIDE_dashboard.components.country_names import ISO3_TO_COUNTRY  # noqa: E402

from fetch_oecd_compute import fetch_az_avail  # noqa: E402

ABS_CSV = ROOT / "data" / "SIDE 2027 - Absolute.csv"
REL_CSV = ROOT / "data" / "SIDE 2027 - Relative.csv"

COUNT_COLUMN = "Availability zones hosting high AI capability (Tier 1) GPUs"
SHARE_COLUMN = "% of availability zones hosting high AI capability (Tier 1) GPUs"

UNIT_COUNT = "Count of AZs"
UNIT_SHARE = "Percentage of total AZs"
TIER1_FIELD = "az_has_training_gpu"


def _fmt(value: object) -> str:
    """Render a number the SIDE way: integers plain, else trimmed to 6 dp."""
    if value is None:
        return ""
    number = float(value)
    if number == int(number):
        return str(int(number))
    return f"{round(number, 6):.6f}".rstrip("0").rstrip(".")


def _tier1_by_country(rows: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    """Split ``az_avail`` into (count, share) dicts keyed on canonical name."""
    counts: dict[str, str] = {}
    shares: dict[str, str] = {}
    for row in rows:
        iso3 = str(row.get("country", "")).strip().upper()
        if iso3 == "ALL":
            continue
        name = ISO3_TO_COUNTRY.get(iso3)
        if name is None:
            continue
        value = _fmt(row.get(TIER1_FIELD))
        unit = str(row.get("unit", "")).strip()
        if unit == UNIT_COUNT:
            counts[name] = value
        elif unit == UNIT_SHARE:
            shares[name] = value
    return counts, shares


def _append_column(
    path: Path,
    column: str,
    values: dict[str, str],
    key_index: int,
    drop: tuple[str, ...],
) -> int:
    """Append ``column`` to ``path`` keyed on the country cell at ``key_index``.

    Any column named in ``drop`` from a previous run is removed first, so the
    build is idempotent and an indicator never lingers in the wrong file.
    Returns the number of data rows populated.
    """
    rows = list(csv.reader(path.open(newline="", encoding="utf-8")))
    header, body = rows[0], rows[1:]

    existing = [i for i, col in enumerate(header) if col in drop]
    if existing:
        header = [col for i, col in enumerate(header) if i not in existing]
        body = [[v for i, v in enumerate(row) if i not in existing] for row in body]

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow([*header, column])
        writer.writerows([*row, values.get(row[key_index], "")] for row in body)

    return sum(1 for row in body if row[key_index] in values)


def main() -> int:
    for path in (ABS_CSV, REL_CSV):
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")

    counts, shares = _tier1_by_country(fetch_az_avail())
    indicator_columns = (COUNT_COLUMN, SHARE_COLUMN)

    covered_abs = _append_column(
        ABS_CSV, COUNT_COLUMN, counts, key_index=0, drop=indicator_columns
    )
    covered_rel = _append_column(
        REL_CSV, SHARE_COLUMN, shares, key_index=1, drop=indicator_columns
    )

    print(f"Wrote {ABS_CSV.name}: {covered_abs} countries populated ({COUNT_COLUMN})")
    print(f"Wrote {REL_CSV.name}: {covered_rel} countries populated ({SHARE_COLUMN})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
