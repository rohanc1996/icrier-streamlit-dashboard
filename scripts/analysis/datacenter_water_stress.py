"""Build the 2027 data-centre water-stress indicator.

The indicator asks a narrow question: given the digital infrastructure a country
has, how badly is it sited with respect to water?  Each facility inherits the
Aqueduct baseline water-stress score of the sub-basin it occupies (0-5, where 5
is more than 80% of renewable supply withdrawn).  A country's value is the
capacity-weighted mean of those scores rescaled to 0-100.

Weighting is the one real assumption.  Epoch AI publishes measured power for
the large AI campuses, so those are weighted in megawatts.  PeeringDB records
how many networks are present at a facility but not its size, so every other
site carries a fixed 5 MW placeholder.  Three variants are emitted alongside the
headline so the assumption can be challenged:

    score             headline, measured MW where available, else 5 MW
    score_kappa15     same with a 15 MW placeholder
    score_netcount    network count (capped at 50) instead of the placeholder
    score_unweighted  every facility counts once

The index is an intensity, not a total: a country with three badly sited
facilities scores the same as one with three hundred.  Absolute exposure is
reported separately as ``mw_high`` so scale is visible without entering the
composite.

Usage
-----
    ./.venv/bin/python scripts/analysis/datacenter_water_stress.py

Reads
-----
    data/derived/water_stress/facilities_joined.csv
    data/SIDE 2027 - Absolute.csv

Writes
------
    data/2027 individual indicators/datacenter_water_stress.csv
    deliverables/water-stress-2027/country_table.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "SIDE_dashboard"))
from components.country_names import COUNTRY_TO_ISO3  # noqa: E402
from core.loader import load_app_data  # noqa: E402

COLUMN = "Data-centre water-stress exposure (0-100)"
KAPPA = 5.0
KAPPA_HIGH = 15.0
MIN_FACILITIES = 3

# The pillar sheets abbreviate eight country names.
SHORT_LABELS = {
    "Dominican Republic": "Dom Rep",
    "Republic of Korea": "S. Korea",
    "Russian Federation": "Russia",
    "Saudi Arabia": "S Arabia",
    "South Africa": "S Africa",
    "United Arab Emirates": "UAE",
    "United Kingdom": "UK",
    "United States of America": "USA",
}
LONG_LABELS = {short: long for long, short in SHORT_LABELS.items()}


def weights(frame: pd.DataFrame, kappa: float) -> pd.Series:
    """Measured MW where Epoch has it, a placeholder elsewhere."""
    measured = pd.to_numeric(frame["mw"], errors="coerce")
    return measured.where(frame["source"].eq("epoch") & measured.notna(), kappa)


def weighted_score(frame: pd.DataFrame, weight: pd.Series) -> pd.Series:
    """Capacity-weighted mean of the Aqueduct 0-5 score, rescaled to 0-100."""
    grouped = frame.assign(_w=weight).groupby("iso3")
    return grouped.apply(
        lambda part: (part["bws_score"] * part["_w"]).sum() / part["_w"].sum()
    ) * 20


def build(facilities: pd.DataFrame, kappa: float = KAPPA) -> pd.DataFrame:
    frame = facilities.copy()
    if "iso3" not in frame.columns:
        frame["iso3"] = frame["gid_0"]
    frame["bws_score"] = pd.to_numeric(frame["bws_score"], errors="coerce")
    frame["cat"] = pd.to_numeric(frame["bws_cat"], errors="coerce")
    frame = frame[frame["bws_score"].notna() & frame["cat"].ge(0)]
    frame["mw"] = pd.to_numeric(frame["mw"], errors="coerce")
    frame["net_count"] = pd.to_numeric(frame["net_count"], errors="coerce")

    frame["_w"] = weights(frame, kappa)
    frame["hi"] = frame["cat"].ge(3).astype(int)
    frame["eh"] = frame["cat"].eq(4).astype(int)

    grouped = frame.groupby("iso3")
    table = pd.DataFrame({
        "n_facilities": grouped.size(),
        "n_high": grouped["hi"].sum(),
        "n_eh": grouped["eh"].sum(),
        "mean_bws_score": grouped["bws_score"].mean(),
        "score": weighted_score(frame, frame["_w"]),
        "score_kappa15": weighted_score(frame, weights(frame, KAPPA_HIGH)),
        "score_netcount": weighted_score(
            frame, frame["net_count"].clip(lower=1, upper=50).fillna(1)
        ),
        "score_unweighted": weighted_score(frame, pd.Series(1.0, index=frame.index)),
    })

    epoch = frame[frame["source"].eq("epoch")]
    measured = epoch.groupby("iso3")["mw"].sum()
    exposed = epoch[epoch["cat"].ge(3)].groupby("iso3")["mw"].sum()
    table["mw_total"] = measured
    table["mw_high"] = exposed.reindex(measured.index).fillna(0.0)
    table["share_mw_high_pct"] = (table["mw_high"] / table["mw_total"] * 100).round(1)

    coarse = frame[frame["geocode_source"].isin(["city", "manual", "unresolved"])]
    table["coarse_geocode_mw"] = coarse.groupby("iso3")["mw"].sum()

    table["flag_min_n"] = table["n_facilities"] < MIN_FACILITIES
    table.loc[table["flag_min_n"], "score"] = np.nan
    return table.reset_index()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facilities", type=Path,
                        default=Path("data/derived/water_stress/facilities_joined.csv"))
    parser.add_argument("--side", type=Path, default=Path("data/SIDE 2027 - Absolute.csv"))
    parser.add_argument("--indicator-out", type=Path,
                        default=Path("data/2027 individual indicators/datacenter_water_stress.csv"))
    parser.add_argument("--table-out", type=Path,
                        default=Path("deliverables/water-stress-2027/country_table.csv"))
    parser.add_argument("--pillar-sheet", type=Path,
                        default=Path("data/2027 pillar-wise/SIDE 2027 Absolute - Sustain.csv"))
    parser.add_argument("--no-sync-pillar", dest="sync_pillar", action="store_false",
                        help="skip writing the indicator into the pillar-wise sheet")
    parser.set_defaults(sync_pillar=True)
    args = parser.parse_args()

    facilities = pd.read_csv(args.facilities)
    print(f"  {len(facilities):,} facilities matched to basins")

    table = build(facilities)

    data = load_app_data(args.side)
    countries = pd.DataFrame({
        "Country": data.country_list,
        "iso3": [COUNTRY_TO_ISO3.get(name) for name in data.country_list],
    })
    merged = countries.merge(table, on="iso3", how="left")

    missing = merged.loc[merged["n_facilities"].isna(), "Country"].tolist()
    flagged = merged.loc[merged["flag_min_n"].fillna(False), "Country"].tolist()
    print(f"  {merged['score'].notna().sum()}/{len(merged)} countries scored")
    print(f"  no facility records: {missing}")
    print(f"  below n={MIN_FACILITIES}: {flagged}")

    score = merged["score"].dropna()
    print(f"  median {score.median():.1f} | mean {score.mean():.1f} | "
          f"range {score.min():.1f}-{score.max():.1f}")
    print(f"  weighting robustness: weighted vs unweighted r="
          f"{merged['score'].corr(merged['score_unweighted']):.3f}, "
          f"kappa 5 vs 15 r={merged['score'].corr(merged['score_kappa15']):.3f}")
    print(f"  measured {merged['mw_total'].sum():,.0f} MW, "
          f"{merged['mw_high'].sum():,.0f} MW in basins above 40% "
          f"({merged['mw_high'].sum() / merged['mw_total'].sum() * 100:.1f}%)")

    rank = merged.dropna(subset=["score"]).sort_values("score", ascending=False)
    print("\n  highest exposure:")
    print(rank.head(8)[["Country", "n_facilities", "score"]].to_string(index=False))
    print("  lowest exposure:")
    print(rank.tail(6)[["Country", "n_facilities", "score"]].to_string(index=False))

    indicator = merged[["Country", "score"]].rename(columns={"score": COLUMN})
    indicator[COLUMN] = indicator[COLUMN].round(1)
    args.indicator_out.parent.mkdir(parents=True, exist_ok=True)
    indicator.to_csv(args.indicator_out, index=False)
    print(f"\n  wrote {args.indicator_out}")

    args.table_out.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.table_out, index=False)
    print(f"  wrote {args.table_out}")

    if args.sync_pillar:
        sync_pillar_sheet(args.pillar_sheet, indicator)
        print(f"  synced {args.pillar_sheet} — run scripts/build_2027_absolute.py next")
    return 0


def sync_pillar_sheet(path: Path, indicator: pd.DataFrame) -> None:
    """Insert or replace this indicator's row in the pillar-wise sheet.

    The pillar sheets are indicator rows by country columns, with a short-label
    header row underneath the column names.  The edit is byte-preserving for
    every other line: these sheets mix CRLF and LF endings, and rewriting them
    through a CSV writer would show the whole file as changed.  Idempotent: an
    existing row for the indicator is replaced rather than duplicated.
    """
    import csv
    import io

    text = path.read_bytes().decode("utf-8")
    lines = text.splitlines(keepends=True)
    terminator = "\r\n" if text.count("\r\n") >= text.count("\n") / 2 else "\n"

    def fields(line: str) -> list[str]:
        return next(csv.reader(io.StringIO(line.rstrip("\r\n"))))

    header = fields(lines[0])
    start = header.index("Country") + 1
    src_countries = header[start:]
    values = dict(zip(indicator["Country"], indicator[COLUMN].astype(str)))

    kept = [line for line in lines
            if not (len(fields(line)) > 3 and fields(line)[3].strip() == COLUMN)]

    numbers = [int(fields(line)[2]) for line in kept[2:]
               if len(fields(line)) > 2 and fields(line)[2].strip().isdigit()]

    row = [""] * len(header)
    row[0] = "SUSTAINABILITY"
    row[2] = str(max(numbers, default=0) + 1)
    row[3] = COLUMN
    for offset, country in enumerate(src_countries):
        # Header may use the long name or one of the eight short labels.
        long_name = LONG_LABELS.get(country, country)
        value = str(values.get(country) or values.get(long_name) or "")
        row[start + offset] = "" if value.lower() == "nan" else value

    buffer = io.StringIO()
    csv.writer(buffer, lineterminator=terminator).writerow(row)
    if kept and not kept[-1].endswith(("\n", "\r")):
        kept[-1] += terminator
    path.write_bytes(("".join(kept) + buffer.getvalue()).encode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
