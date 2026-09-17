"""Loading and cleaning the SIDE digital-economy dataset.

Mirrors the cleaning steps in ``skewed_column_scaling_analysis.ipynb``
(cells 1-2):

1. Normalise column headers (collapse duplicate spaces, strip source URLs) and
   drop pandas' auto-named ``Unnamed: N`` columns (stray cells in the source
   sheet, not real indicators).
2. Parse cells into numbers (strip, remove thousands separators, treat
   ``-`` / ``--`` / blank cells as missing).
3. Keep only real country rows (the file ends with summary rows such as
   ``Coefficient of variation`` and blank rows).
4. Keep numeric columns that have at least ``MIN_VALID_VALUES`` non-missing
   observations.

The result is an :class:`AppData` object that all dashboard views consume.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from . import chips_hierarchy as H
from .columns import canonical_key

# The datasets live in the repository root's ``data/`` folder, one level up
# from the SIDE_dashboard package folder.  Each *year* has two base-score
# variants (relative-normalised values and the raw absolute values); the
# dashboard's sidebar selects both the year and the variant.
#
# The years below are pre-registered: the app already knows where 2025 and 2027
# files *would* live, and only exposes a year once at least one of its files is
# actually present (see ``available_years``).  Dropping
# ``SIDE <year> - Relative.csv`` / ``SIDE <year> - Absolute.csv`` into ``data/``
# is therefore all it takes for a new edition to appear in the selector.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATASET_YEARS: tuple[str, ...] = ("2025", "2026", "2027")
DEFAULT_YEAR = "2026"


def _paths_for(year: str) -> dict[str, Path]:
    """Expected file paths for one year's two base-score variants."""
    return {
        "Relative": DATA_DIR / f"SIDE {year} - Relative.csv",
        "Absolute": DATA_DIR / f"SIDE {year} - Absolute.csv",
    }


DATASETS: dict[str, dict[str, Path]] = {year: _paths_for(year) for year in DATASET_YEARS}
# Filenames of relative-normalised files (these need column renaming).  Matched
# by pattern rather than by a fixed set so future years are handled with no code
# change; the pattern deliberately excludes the "AI augmented ... Index" files.
_RELATIVE_NAME_RE = re.compile(r"^SIDE\s+\d{4}\s*-\s*Relative\.csv$", re.IGNORECASE)


def sources_for(year: str) -> dict[str, Path]:
    """Variants of ``year`` whose files actually exist on disk."""
    return {v: p for v, p in DATASETS.get(year, {}).items() if Path(p).exists()}


def available_years() -> list[str]:
    """Registered years that have at least one dataset file present."""
    return [year for year in DATASET_YEARS if sources_for(year)]


def default_year() -> str | None:
    """The preferred year if present, else the newest available one."""
    years = available_years()
    if DEFAULT_YEAR in years:
        return DEFAULT_YEAR
    return years[-1] if years else None


# Backwards-compatible aliases for scripts / tests that predate the year switch.
DATA_SOURCES = DATASETS[DEFAULT_YEAR]
DATA_FILE = DATA_SOURCES["Absolute"]  # headless default (scripts / tests)
MIN_VALID_VALUES = 5

# --------------------------------------------------------------------------
# Relative dataset: rename its "relative" (per-GNI / per-capita / % / per-user)
# main-block headers to the canonical absolute-equivalent header names that the
# CHIPS spec, loader config and dashboard are keyed on.  Columns without a
# canonical counterpart are left as-is (extra addable indicators) or dropped.
# --------------------------------------------------------------------------
RELATIVE_TO_CANONICAL = {
    "Price of mobile data and voice basket (HC) (% of GNI PC)": "Price of mobile data and voice basket (HC) (PPP)",
    "Price of mobile data and voice basket (HC) (% of GNI PC).1": "Price of mobile data and voice basket (LC) (PPP)",
    "Price of cheapest smartphone (% of GNI per capita)": "Price of cheapest smartphone (PPP$)",
    "Price of fixed broadband internet (% of GNI)": "Price of fixed broadband internet (PPP)",
    "Median Mobile Download Speeds (Mbps)": "Median Mobile Download Speeds (Mbps)",
    "Median Fixed Broadband Download Speed (Mbps)": "Median Fixed Broadband Download Speed (Mbps)",
    "% of population using the internet": "Number of Internet Users (absolute numbers)",
    "Mobile Cellular Subscriptions per 100 population": "Mobile Cellular Subscriptions in millions (absolute numbers)",
    "% of Population covered by LTE": "Population covered by LTE (Absolute numbers)",
    "% of population using smartphones users": "Number of smartphone users (million)",
    "% of internet users (16-64 years) using social media for work related activities": "Number of internet users (16-64 years) using social media for work related activities",
    "Percent of internet users using digital food delivery platforms": "Number of users of digital food delivery platforms (millions)",
    "Percent of internet users using digital health applications": "Number of users of digital health applications",
    "Percent of internet users using e-commerce users": "Number of e-commerce users",
    "Consumer Spend per internet user on Mobile Apps (millions USD) PPP per internet user": "Consumer Spend on Mobile Apps (millions USD)",
    "Percent of internet users using video on demand users": "Number of video on demand users",
    "Fixed-broadband Internet traffic per subscriber (GB)": "Fixed-broadband Internet traffic (EB)",
    "Mobile broadband internet traffic (GB per subscription)": "Mobile broadband internet traffic (EB)",
    "Value of digital payment transactions (PPP$ adjusted) per internet user": "Value of digital payment transactions (millions of dollars)",
    "% of internet users who made or received a digital payment": "Users of Digital Payments (in millions)",
    "Total digitally delivered services (million USD) as percent of GDP USD": "Total digitally delivered services (million USD)",
    "ICT sector employment (% of Total Labour force)": "Employment: ICT sector (thousands)",
    "Number of Start-ups per limited liability company": "Number of Start-ups",
    "Valuation of Unicorns as a percent of GDP": "Valuation of Unicorns (Millions of USD)",
    "Total funding till date of Startups having their Head Quarters or atleast one office location in India per startup (Millions of USD)": "Total funding till date of Startups having their Head Quarters or atleast one office location in India (Millions of USD)",
    "Consumer IoT revenues (USD PPP$ adjusted) per internet user": "Consumer and Industrial IoT revenues (millions of USD)",
    "AR/ VR revenues (PPP$ adjusted) per smartphone user": "AR/ VR revenues (millions of USD)",
    "Metaverse revenue (PPP$ adjusted) per smartphone user": "Metaverse revenue (millions of USD)",
    "DeFi revenue (millions of USD PPP$ adjusted) per internet user": "DeFi revenue (millions of USD)",
    "Robotics revenue (millions of USD)": "Robotics revenue (millions of USD)",
    "Drones revenue (millions of USD)": "Drones revenue (millions of USD)",
    "Crypto Index Score": "Crypto Index Score",
    "Cybersecurity revenue (PPP exchange rate adjusted ) in million $ , per internet users": "Cybersecurity revenue (Mn USD)",
    "Number of Secure servers per internet user": "Number of Secure servers",
    "Ransomware attacks detected per month as a % of internet users": "Ransomware attacks 30 day average",
    "Ransomware victims per million internet users": "Ransomware victims",
    "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)": "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)",
    "E-waste generated (kg per capita) - directly from source": "E-waste generated (million kg)",
    "Share of energy startups that are digital": "Number of energy and digital startups",
    "VC investments in AI and environmental sustainability by country (USD million) per capita": "VC investments in AI and environmental sustainability by country (USD million)",
    "Patents filed (2000-2023) in Smart Grids as a % of enabling tech patents": "Patents filed (2000-2024) in Smart Grids",
    "Patents filed (2000-2023) in Information/Communication Technologies for Electromobility as a % of total patents filed": "Patents filed (2000-2024) in Information/Communication Technologies for Electromobility",
    "Renewable energy share of electricity production (%)": "Total renewable energy production (GWh)",
    "Relative AAL by Climate (% of Exposed value) for the Telecom Sector - Existing Climate": "AAL by Climate (Million USD) for the Telecom Sector- Existing Climate",
}
# Relative-file columns that are metadata or duplicate variants, never indicators.
RELATIVE_DROP = {"BLOC"}

# --------------------------------------------------------------------------
# Plain-language labels and organisation (keys are *normalised* column names).
# --------------------------------------------------------------------------

FRIENDLY_NAMES = {
    "Price of mobile data and voice basket (HC) (PPP)": "Mobile data & voice basket price (HC, PPP)",
    "Price of mobile data and voice basket (LC) (PPP)": "Mobile data & voice basket price (LC, PPP)",
    "Price of cheapest smartphone (PPP$)": "Cheapest smartphone price (PPP $)",
    "Price of fixed broadband internet (PPP)": "Fixed broadband price (PPP $)",
    "Median Mobile Download Speeds (Mbps)": "Mobile download speed (Mbps)",
    "Median Fixed Broadband Download Speed (Mbps)": "Fixed broadband download speed (Mbps)",
    "Number of Internet Users (absolute numbers)": "Internet users",
    "Mobile Cellular Subscriptions in millions (absolute numbers)": "Mobile cellular subscriptions (millions)",
    "Population covered by LTE (Absolute numbers)": "Population covered by LTE",
    "Number of smartphone users (million)": "Smartphone users (millions)",
    "Gender gap - Number of women that need to use the internet (or stop using the internet, if negative) to achieve parity in internet penetration rate": "Gender gap in internet use",
    "Number of internet users (16-64 years) using social media for work related activities": "Social media use for work (16-64 yrs)",
    "Number of users of digital food delivery platforms (millions)": "Food delivery platform users (millions)",
    "Number of users of digital health applications": "Digital health app users",
    "Number of e-commerce users": "E-commerce users",
    "Consumer Spend on Mobile Apps (millions USD)": "Consumer app spend (USD millions)",
    "Number of video on demand users": "Video-on-demand users",
    "Fixed-broadband Internet traffic (EB)": "Fixed broadband traffic (EB)",
    "Mobile broadband internet traffic (EB)": "Mobile broadband traffic (EB)",
    "Value of digital payment transactions (millions of dollars)": "Digital payment transaction value (USD millions)",
    "Users of Digital Payments (in millions)": "Digital payment users (millions)",
    "Number of people who received public sector wages (% of public sector wage recipients, age 15 +) per 1000 adults": "Public sector wages paid digitally (per 1,000 adults)",
    "Number of mobile money and internet banking transactions per 1000 adults": "Mobile money / internet banking transactions (per 1,000 adults)",
    "Number of mobile money and internet banking transactions": "Mobile money / internet banking transactions",
    "ICT Services Export (million USD)": "ICT services exports (USD millions)",
    "Total digitally delivered services (million USD)": "Digitally delivered services (USD millions)",
    "IT market Capitalisation in USD": "IT market capitalisation (USD)",
    "Employment: ICT sector (thousands)": "ICT sector employment (thousands)",
    "Employment: ICT services (thousands)": "ICT services employment (thousands)",
    "Number of Start-ups": "Number of start-ups",
    "Valuation of Unicorns (Millions of USD)": "Unicorn valuations (USD millions)",
    "Total funding till date of Startups having their Head Quarters or atleast one office location in India (Millions of USD)": "Start-up funding to date (USD millions)",
    "Consumer and Industrial IoT revenues (millions of USD)": "Consumer & industrial IoT revenue (USD millions)",
    "AR/ VR revenues (millions of USD)": "AR/VR revenue (USD millions)",
    "Metaverse revenue (millions of USD)": "Metaverse revenue (USD millions)",
    "DeFi revenue (millions of USD)": "DeFi revenue (USD millions)",
    "Robotics revenue (millions of USD)": "Robotics revenue (USD millions)",
    "Drones revenue (millions of USD)": "Drones revenue (USD millions)",
    "Crypto Index Score": "Crypto index score",
    "Cybersecurity revenue (Mn USD)": "Cybersecurity revenue (USD millions)",
    "Number of Secure servers": "Secure servers",
    "Ransomware attacks 30 day average": "Ransomware attacks (30-day average)",
    "Ransomware victims": "Ransomware victims",
    "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)": "Email leaks (quarterly average)",
    "E-waste generated (million kg)": "E-waste generated (million kg)",
    "Number of energy and digital startups": "Energy & digital start-ups",
    "VC investments in AI and environmental sustainability by country (USD million)": "VC investment in AI & sustainability (USD millions)",
    "Patents filed (2000-2024) in Smart Grids": "Smart-grid patents (2000-2024)",
    "Patents filed (2000-2024) in Information/Communication Technologies for Electromobility": "Electromobility ICT patents (2000-2024)",
    "Net electricity production from Renewables (Hydro, Geo, Solar, Wind, Other) (GWh)": "Renewable electricity production (GWh)",
    "Total renewable energy production (GWh)": "Total renewable energy production (GWh)",
    "AAL by Climate (Million USD) for the Telecom Sector- Existing Climate": "Climate-adjusted telecom losses (USD millions)",
    "Number of AI users": "Number of AI users",
    "Compute capacity": "Compute capacity",
    "Open Data Score": "Open data score",
    "AI Infrastructure": "AI infrastructure score",
    "AI Infrastructure.1": "AI infrastructure score (2)",
    "Compute Capacity (Rmax) in Millions": "Compute capacity (Rmax, millions)",
    "Apps and Platforms": "Apps & platforms score",
    "Development: Open Source models score": "Open-source models score",
    "Relative AI Skill Penetration": "Relative AI skill penetration",
    "AI Talent Pillar Score": "AI talent score",
    "Total AI Private Investment in Millions": "Total AI private investment (USD millions)",
    "Newly Funded AI Companies": "Newly funded AI companies",
    "AI commercial": "AI commercial score",
    "AI Innovation - Research": "AI research innovation score",
    "AI Research and Development- score": "AI R&D score",
    "Safety and security": "AI safety & security score",
    "Responsible AI - Conference Submissions on RAI Topics (Total)": "Responsible-AI conference submissions",
    "Public trust score": "Public trust score",
}
# Indicator categories are derived at load time from the CHIPS hierarchy
# (``core/chips_hierarchy.py``): each indicator is grouped under its
# "PILLAR · SUB-PILLAR".  Dataset indicators that are not part of the published
# framework are labelled ``NOT_IN_FRAMEWORK_LABEL``.
NOT_IN_FRAMEWORK_LABEL = "Other (not in framework)"

# Whether a HIGHER value of the indicator is *better* for a country.
# Price / risk / waste indicators are set to False.
HIGHER_IS_BETTER = {
    "Price of mobile data and voice basket (HC) (PPP)": False,
    "Price of mobile data and voice basket (LC) (PPP)": False,
    "Price of cheapest smartphone (PPP$)": False,
    "Price of fixed broadband internet (PPP)": False,
    "Gender gap - Number of women that need to use the internet (or stop using the internet, if negative) to achieve parity in internet penetration rate": False,
    "Ransomware attacks 30 day average": False,
    "Ransomware victims": False,
    "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)": False,
    "E-waste generated (million kg)": False,
    "AAL by Climate (Million USD) for the Telecom Sector- Existing Climate": False,
}
# Canonical-key lookups so a later edition whose headers carry shifted year
# ranges still resolves to the same friendly name / direction.  Exact keys are
# a subset of these, so one normalised lookup replaces the exact dict lookup.
_FRIENDLY_BY_KEY = {canonical_key(k): v for k, v in FRIENDLY_NAMES.items()}
_HIGHER_IS_BETTER_BY_KEY = {canonical_key(k): v for k, v in HIGHER_IS_BETTER.items()}


def resolve_friendly_name(column: str) -> str:
    """Friendly label for a dataset column, tolerant of year-range drift."""
    return _FRIENDLY_BY_KEY.get(canonical_key(column), column)


def resolve_higher_is_better(column: str) -> bool:
    """Whether a higher value is better, tolerant of year-range drift."""
    return _HIGHER_IS_BETTER_BY_KEY.get(canonical_key(column), True)


def normalize_column_name(col: str) -> str:
    """Collapse whitespace and strip trailing source URLs from a header."""
    col = str(col).strip()
    col = re.sub(r"\s+", " ", col)
    if "https://" in col:
        col = col.split(" https://", 1)[0].rstrip()
    return col


def shrink_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse runs of whitespace in every cell to a single space and strip.

    Source sheets carry stray tabs, newlines and non-breaking spaces that would
    otherwise cause mismatched country names and unparsable numbers.
    """
    return df.apply(
        lambda col: col.map(
            lambda v: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v
        )
    )


def parse_numeric(series: pd.Series) -> pd.Series:
    """Convert messy cells (commas, dashes, blanks) into numbers or NaN."""
    cleaned = series.astype(str).str.strip()
    missing = cleaned.isin(["", "-", "—", "–"])
    cleaned = cleaned.str.replace(",", "", regex=False)
    return pd.to_numeric(cleaned.where(~missing, np.nan), errors="coerce")


def _dedupe_columns(columns: pd.Index) -> pd.Index:
    """Make repeated column names unique (e.g. two 'AI Infrastructure' cells)."""
    seen: dict[str, int] = {}
    out = []
    for col in columns:
        n = seen.get(col, 0)
        seen[col] = n + 1
        out.append(col if n == 0 else f"{col} ({n + 1})")
    return pd.Index(out)


def _relative_rename_map(columns) -> dict[str, str]:
    """Map a relative file's headers to their canonical absolute names.

    Exact names are tried first; otherwise the header is matched on its
    canonical key so a later edition whose year ranges shifted still translates.
    """
    by_key: dict[str, str] = {}
    for source, target in RELATIVE_TO_CANONICAL.items():
        by_key.setdefault(canonical_key(source), target)
    mapping: dict[str, str] = {}
    for col in columns:
        if col in RELATIVE_TO_CANONICAL:
            mapping[col] = RELATIVE_TO_CANONICAL[col]
        else:
            target = by_key.get(canonical_key(col))
            if target and target != col:
                mapping[col] = target
    return mapping


def _indicator_categories(columns) -> dict[str, str]:
    """Map each dataset column to its CHIPS "PILLAR · SUB-PILLAR" group.

    Columns that are not part of the published hierarchy are absent from the
    result; the caller labels those ``NOT_IN_FRAMEWORK_LABEL``.
    """
    pillars, _ = H.resolve_hierarchy(columns)
    out: dict[str, str] = {}
    for pillar in pillars:
        for sub in pillar.sub_pillars:
            leaves = [leaf for g in sub.groups for leaf in g.leaves] if sub.groups else sub.leaves
            for leaf in leaves:
                if leaf.column:
                    out[leaf.column] = f"{pillar.name} · {sub.name}"
    return out


@dataclass
class AppData:
    """Everything the dashboard needs, loaded once and cached."""

    df: pd.DataFrame
    numeric_df: pd.DataFrame
    indicators: list[str]
    country_list: list[str]
    friendly_names: dict[str, str]
    categories: dict[str, str]
    higher_is_better: dict[str, bool]


@st.cache_data(show_spinner="Loading the SIDE dataset...")
def load_app_data(path: Path | str = DATA_FILE) -> AppData:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw = shrink_whitespace(raw)
    raw.columns = _dedupe_columns(pd.Index(normalize_column_name(c) for c in raw.columns))

    # The relative dataset renames its main indicators to per-GNI / per-capita /
    # % measures; translate them back to the canonical headers the rest of the
    # app (hierarchy, friendly names, higher-is-better) is keyed on.  Detected by
    # filename so future years are covered without touching this module.
    if _RELATIVE_NAME_RE.match(path.name):
        raw = raw.rename(columns=_relative_rename_map(raw.columns))
        raw = raw.loc[:, ~raw.columns.isin(RELATIVE_DROP)]
        raw.columns = _dedupe_columns(raw.columns)

    # Drop pandas' auto-generated "Unnamed: N" columns. They are stray cells in
    # the source sheet, not real indicators, so they must never reach the
    # dashboard (indicator lists, charts, tables or CHIPS calculations).
    raw = raw.loc[:, ~raw.columns.astype(str).str.match(r"^Unnamed:\s*\d+$")]

    # Keep only real country rows (drop the summary rows at the end of the file).
    country_clean = raw["Country"].astype(str).str.strip()
    real = (country_clean != "") & (country_clean != "Coefficient of variation")
    df = raw.loc[real].copy().reset_index(drop=True)

    numeric_df = pd.DataFrame({"Country": df["Country"].astype(str).str.strip()})
    for col in df.columns:
        if col == "Country":
            continue
        numeric_df[col] = parse_numeric(df[col])

    indicators = [
        col
        for col in numeric_df.columns
        if col != "Country" and int(numeric_df[col].notna().sum()) >= MIN_VALID_VALUES
    ]

    friendly_names = {c: resolve_friendly_name(c) for c in numeric_df.columns}
    pillar_categories = _indicator_categories(numeric_df.columns)
    categories = {
        c: pillar_categories.get(c, NOT_IN_FRAMEWORK_LABEL) for c in indicators
    }
    higher_is_better = {c: resolve_higher_is_better(c) for c in indicators}

    return AppData(
        df=df,
        numeric_df=numeric_df,
        indicators=indicators,
        country_list=numeric_df["Country"].tolist(),
        friendly_names=friendly_names,
        categories=categories,
        higher_is_better=higher_is_better,
    )




