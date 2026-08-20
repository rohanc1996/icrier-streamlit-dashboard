"""Loading and cleaning the SIDE 2026 dataset.

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

# The dataset lives next to the project root (repository root), one level up
# from the SIDE_dashboard package folder.
DATA_FILE = Path(__file__).resolve().parents[2] / "SIDE 2026 - Rohan - Absolute.csv"
MIN_VALID_VALUES = 5

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
# Broad subject areas used to organise the indicator lists.
CATEGORIES = {
    "Price of mobile data and voice basket (HC) (PPP)": "Affordability",
    "Price of mobile data and voice basket (LC) (PPP)": "Affordability",
    "Price of cheapest smartphone (PPP$)": "Affordability",
    "Price of fixed broadband internet (PPP)": "Affordability",
    "Median Mobile Download Speeds (Mbps)": "Connectivity & access",
    "Median Fixed Broadband Download Speed (Mbps)": "Connectivity & access",
    "Number of Internet Users (absolute numbers)": "Connectivity & access",
    "Mobile Cellular Subscriptions in millions (absolute numbers)": "Connectivity & access",
    "Population covered by LTE (Absolute numbers)": "Connectivity & access",
    "Number of smartphone users (million)": "Connectivity & access",
    "Gender gap - Number of women that need to use the internet (or stop using the internet, if negative) to achieve parity in internet penetration rate": "Digital economy",
    "Number of internet users (16-64 years) using social media for work related activities": "Digital economy",
    "Number of users of digital food delivery platforms (millions)": "Digital economy",
    "Number of users of digital health applications": "Digital economy",
    "Number of e-commerce users": "Digital economy",
    "Consumer Spend on Mobile Apps (millions USD)": "Digital economy",
    "Number of video on demand users": "Digital economy",
    "Fixed-broadband Internet traffic (EB)": "Digital economy",
    "Mobile broadband internet traffic (EB)": "Digital economy",
    "Value of digital payment transactions (millions of dollars)": "Digital economy",
    "Users of Digital Payments (in millions)": "Digital economy",
    "Number of people who received public sector wages (% of public sector wage recipients, age 15 +) per 1000 adults": "Digital economy",
    "Number of mobile money and internet banking transactions per 1000 adults": "Digital economy",
    "Number of mobile money and internet banking transactions": "Digital economy",
    "ICT Services Export (million USD)": "Digital economy",
    "Total digitally delivered services (million USD)": "Digital economy",
    "IT market Capitalisation in USD": "Digital economy",
    "Employment: ICT sector (thousands)": "Digital economy",
    "Employment: ICT services (thousands)": "Digital economy",
    "Number of Start-ups": "Start-ups & innovation",
    "Valuation of Unicorns (Millions of USD)": "Start-ups & innovation",
    "Total funding till date of Startups having their Head Quarters or atleast one office location in India (Millions of USD)": "Start-ups & innovation",
    "Number of energy and digital startups": "Start-ups & innovation",
    "VC investments in AI and environmental sustainability by country (USD million)": "Start-ups & innovation",
    "Patents filed (2000-2024) in Smart Grids": "Start-ups & innovation",
    "Patents filed (2000-2024) in Information/Communication Technologies for Electromobility": "Start-ups & innovation",
    "Consumer and Industrial IoT revenues (millions of USD)": "Emerging technologies",
    "AR/ VR revenues (millions of USD)": "Emerging technologies",
    "Metaverse revenue (millions of USD)": "Emerging technologies",
    "DeFi revenue (millions of USD)": "Emerging technologies",
    "Robotics revenue (millions of USD)": "Emerging technologies",
    "Drones revenue (millions of USD)": "Emerging technologies",
    "Crypto Index Score": "Emerging technologies",
    "Number of AI users": "AI ecosystem",
    "Compute capacity": "AI ecosystem",
    "Open Data Score": "AI ecosystem",
    "AI Infrastructure": "AI ecosystem",
    "AI Infrastructure.1": "AI ecosystem",
    "Compute Capacity (Rmax) in Millions": "AI ecosystem",
    "Apps and Platforms": "AI ecosystem",
    "Development: Open Source models score": "AI ecosystem",
    "Relative AI Skill Penetration": "AI ecosystem",
    "AI Talent Pillar Score": "AI ecosystem",
    "Total AI Private Investment in Millions": "AI ecosystem",
    "Newly Funded AI Companies": "AI ecosystem",
    "AI commercial": "AI ecosystem",
    "AI Innovation - Research": "AI ecosystem",
    "AI Research and Development- score": "AI ecosystem",
    "Safety and security": "AI ecosystem",
    "Responsible AI - Conference Submissions on RAI Topics (Total)": "AI ecosystem",
    "Public trust score": "AI ecosystem",
    "Cybersecurity revenue (Mn USD)": "Security & trust",
    "Number of Secure servers": "Security & trust",
    "Ransomware attacks 30 day average": "Security & trust",
    "Ransomware victims": "Security & trust",
    "Total number of email leaks (Quarterly average) (2022 Q3 - 2025 Q3)": "Security & trust",
    "E-waste generated (million kg)": "Sustainability & energy",
    "Net electricity production from Renewables (Hydro, Geo, Solar, Wind, Other) (GWh)": "Sustainability & energy",
    "Total renewable energy production (GWh)": "Sustainability & energy",
    "AAL by Climate (Million USD) for the Telecom Sector- Existing Climate": "Sustainability & energy",
}

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
def normalize_column_name(col: str) -> str:
    """Collapse whitespace and strip trailing source URLs from a header."""
    col = str(col).strip()
    col = re.sub(r"\s+", " ", col)
    if "https://" in col:
        col = col.split(" https://", 1)[0].rstrip()
    return col


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


@st.cache_data(show_spinner="Loading the SIDE 2026 dataset...")
def load_app_data(path: Path | str = DATA_FILE) -> AppData:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")

    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    raw.columns = _dedupe_columns(pd.Index(normalize_column_name(c) for c in raw.columns))

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

    friendly_names = {c: FRIENDLY_NAMES.get(c, c) for c in numeric_df.columns}
    categories = {c: CATEGORIES.get(c, "Other") for c in indicators}
    higher_is_better = {c: HIGHER_IS_BETTER.get(c, True) for c in indicators}

    return AppData(
        df=df,
        numeric_df=numeric_df,
        indicators=indicators,
        country_list=numeric_df["Country"].tolist(),
        friendly_names=friendly_names,
        categories=categories,
        higher_is_better=higher_is_better,
    )




