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
from core import scaling  # noqa: E402
from core.loader import load_app_data  # noqa: E402
from views import (  # noqa: E402
    chips_explorer,
    correlation_explorer,
    country_explorer,
    outlier_explorer,
    scaling_comparator,
)

PAGES = {
    "🏆 CHIPS Index Explorer": chips_explorer,
    "🌍 Country Explorer": country_explorer,
    "⚖️ Scaling Comparator": scaling_comparator,
    "🔬 Correlation Explorer": correlation_explorer,
    "🕵️ Outlier Explorer": outlier_explorer,
}


def main() -> None:
    # Compact topbar shown on every tab: title + dataset tagline on one row.
    title_col, tagline_col = st.columns([3, 1], vertical_alignment="center")
    with title_col:
        st.markdown("## 🌐 SIDE Digital Economy Dashboard")
    with tagline_col:
        st.markdown(
            "Interactive companion to the SIDE 2026 dataset. 71 countries, 60+ indicators."
        )
    st.divider()

    with st.sidebar:
        choice = st.radio("Navigate", list(PAGES.keys()), key="nav", label_visibility="collapsed")
        st.divider()
        st.caption(
            "**Scoring method** — how raw values become 0–1 scores. Used by the "
            "single-score pages; the comparator and correlation pages always "
            "show all four methods."
        )
        st.radio(
            "Scoring method",
            list(scaling.ALL_METHODS),
            format_func=lambda m: scaling.METHOD_SHORT_LABELS[m],
            index=scaling.ALL_METHODS.index(scaling.METHOD_CAPPED),
            key="scaling_method",
            horizontal=True,
            help="Scores are inverted where a low raw value is better, so 1.0 "
                 "always means 'best'.",
        )
        st.caption(
            "Full-range min-max · 5–95 percentile capped min-max (default) · "
            "log-transformed min-max · z-score (standardized)."
        )

    data = load_app_data()
    method = st.session_state.get("scaling_method", scaling.METHOD_CAPPED)
    PAGES[choice].render(data, method=method)


if __name__ == "__main__":
    main()
