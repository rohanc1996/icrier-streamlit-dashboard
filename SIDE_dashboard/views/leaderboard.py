"""View 5: Rank-based leaderboard."""
from __future__ import annotations

import streamlit as st

from components import ui
from core import rankings

DEFAULT_INDICATOR = "Median Mobile Download Speeds (Mbps)"


def render(data) -> None:
    ui.page_header(
        "🏆 Leaderboard",
        "Every country ranked on one indicator at a time — with the score under "
        "all three scaling methods.",
    )
    ui.explainer(
        "📊",
        "Choose an indicator to see the full ranking, search for a country, "
        "and download the table as CSV. Indicators are grouped by category in "
        "the dropdown.",
    )

    indicator = ui.indicator_selectbox(
        data, "Indicator", key="lb_indicator", default=DEFAULT_INDICATOR, group_categories=True
    )
    if indicator is None:
        return

    table = rankings.rank_table(data, indicator)

    search = st.text_input("🔎 Search by country name", key="lb_search", placeholder="e.g. India, Brazil, Nigeria…")
    if search.strip():
        table = table[table["Country"].str.contains(search.strip(), case=False, na=False)]

    ui.show_table(table, column_config=ui.rank_column_config(data), height=520)

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download leaderboard as CSV",
        csv,
        file_name=f"leaderboard_{indicator[:40].replace(' ', '_')}.csv",
        mime="text/csv",
        key="lb_download",
    )
