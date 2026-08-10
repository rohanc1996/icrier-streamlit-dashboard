"""SIDE Digital Economy Dashboard — interactive companion to the 2026 dataset.

Run from the repository root:

    streamlit run SIDE_dashboard/dashboard.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="SIDE Digital Economy Dashboard",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components import ui  # noqa: E402
from core.loader import load_app_data  # noqa: E402
from views import (  # noqa: E402
    correlation_explorer,
    country_explorer,
    leaderboard,
    outlier_explorer,
    scaling_comparator,
)

PAGES = {
    "🌍 Country Explorer": country_explorer,
    "⚖️ Scaling Comparator": scaling_comparator,
    "🔬 Correlation Explorer": correlation_explorer,
    "🕵️ Outlier Explorer": outlier_explorer,
    "🏆 Leaderboard": leaderboard,
}


def main() -> None:
    with st.sidebar:
        st.title("🌐 SIDE Digital Economy Dashboard")
        st.caption(
            "Interactive companion to the SIDE 2026 dataset — "
            "71 countries, 60+ indicators."
        )
        st.divider()
        choice = st.radio("Navigate", list(PAGES.keys()), key="nav", label_visibility="collapsed")
        st.divider()
        st.caption(
            "**Three scaling methods:** full-range min-max · 5–95 percentile "
            "capped min-max · log-transformed min-max. The capped version is the "
            "most robust choice for reporting."
        )

    data = load_app_data()
    PAGES[choice].render(data)


if __name__ == "__main__":
    main()
