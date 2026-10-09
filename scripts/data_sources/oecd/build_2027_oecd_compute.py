#!/usr/bin/env python3
"""Add the OECD "GPU availability by AI capability" indicators to
``data/SIDE 2027 - Absolute.csv``.

Indicator (CONNECT, not yet part of the scored CHIPS hierarchy)
---------------------------------------------------------------
From the OECD/Oxford ``az_avail`` table, for each country:

  * ``Availability zones hosting high AI capability (Tier 1) GPUs``
      = ``az_has_training_gpu`` on the ``Count of AZs`` rows.
  * ``% of availability zones hosting high AI capability (Tier 1) GPUs``
      = the same field on the ``Percentage of total AZs`` rows.

Tier 1 GPUs are those capable of AI training, fine-tuning and inference
(the "high AI capability" band of the OECD chart).  Higher is better.

Country mapping
---------------
The OECD table keys on ISO-3 codes; SIDE keys on canonical country names.
``SIDE_dashboard/components/country_names.py`` is the single source of truth
for that mapping, so it is imported rather than duplicated.  Codes with no SIDE
row (Bahrain, Taiwan, Hong Kong) and the ``ALL`` aggregate are dropped.  The
remaining 33 SIDE countries are written as empty cells (the file's existing
missing-value convention).

The columns are appended (idempotently: a re-run replaces them) so no existing
column or row is disturbed.

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

COUNT_COLUMN = "Availability zones hosting high AI capability (Tier 1) GPUs"
SHARE_COLUMN = "% of availability zones hosting high AI capability (Tier 1) GPUs"
NEW_COLUMNS = (COUNT_COLUMN, SHARE_COLUMN)

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


def main() -> int:
    if not ABS_CSV.exists():
        raise FileNotFoundError(f"Dataset not found: {ABS_CSV}")

    rows = list(csv.reader(ABS_CSV.open(newline="", encoding="utf-8")))
    header, body = rows[0], rows[1:]
    if header and header[0] != "Country":
        raise ValueError(f"Unexpected first column: {header[0]!r}")

    # Drop the new columns and their values if a previous run added them, so
    # the build is idempotent and column order stays deterministic.
    existing = [i for i, col in enumerate(header) if col in NEW_COLUMNS]
    if existing:
        header = [col for i, col in enumerate(header) if i not in existing]
        body = [[v for i, v in enumerate(row) if i not in existing] for row in body]

    counts, shares = _tier1_by_country(fetch_az_avail())

    out_header = [*header, *NEW_COLUMNS]
    out_body = [
        [*row, counts.get(row[0], ""), shares.get(row[0], "")]
        for row in body
    ]

    with ABS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(out_header)
        writer.writerows(out_body)

    covered = sum(1 for row in body if row[0] in counts)
    print(
        f"Wrote {ABS_CSV.name}: +{len(NEW_COLUMNS)} columns, "
        f"{covered}/{len(body)} countries populated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
