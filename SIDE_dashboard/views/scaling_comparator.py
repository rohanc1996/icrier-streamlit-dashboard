"""View 2: Scaling-method comparator (histograms + rank stability)."""
from __future__ import annotations

import streamlit as st

from components import charts, ui
from core import rankings

DEFAULT_INDICATOR = "Median Mobile Download Speeds (Mbps)"


def render(data) -> None:
    ui.page_header(
        "⚖️ Scaling comparator",
        "Raw numbers are turned into 0–1 scores in three different ways. "
        "This page shows how that choice changes the picture — and which "
        "countries' rankings are most sensitive to it.",
    )
    ui.explainer(
        "🧭",
        "Use the sliders to change the cap window. Watch the middle histogram "
        "and the rank table below update live.",
    )

    indicator = ui.indicator_selectbox(data, "Indicator", key="sc_indicator", default=DEFAULT_INDICATOR)
    if indicator is None:
        return

    c1, c2 = st.columns(2)
    with c1:
        lower = st.slider("Lower cap percentile", 1, 49, 5, key="sc_lower",
                          help="Values below this percentile are pulled up to the cap.")
    with c2:
        upper = st.slider("Upper cap percentile", 51, 99, 95, key="sc_upper",
                          help="Values above this percentile are pulled down to the cap.")

    lower_f, upper_f = lower / 100.0, upper / 100.0

    st.plotly_chart(charts.hist_3panel(data, indicator, lower_f, upper_f), width="stretch")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**Full-range min-max**")
        st.markdown("Simple and easy to explain, but a single extreme value can squash everyone else into a narrow band.")
    with col_b:
        st.markdown(f"**{lower}–{upper} percentile capped**")
        st.markdown("The robust choice for reporting: the scale ignores the extremes, so rankings stay stable.")
    with col_c:
        st.markdown("**Log-transformed min-max**")
        st.markdown("Compresses the upper tail to reflect percentage-like differences, but is less intuitive.")

    st.markdown("### How the ranking changes under each scaling")
    stability = rankings.rank_stability_table(data, indicator, lower_f, upper_f)

    left, right = st.columns([3, 2])
    with left:
        ui.show_table(
            stability[["Country", "value", "rank_full", "rank_capped", "rank_log", "max_swing"]],
            column_config=ui.rank_column_config(data),
            height=400,
        )
    with right:
        st.subheader("Biggest movers")
        st.caption("Countries whose rank moves the most when the scaling method changes.")
        st.plotly_chart(charts.movers_bar(stability), width="stretch")

    avg_swing = float(stability["max_swing"].mean())
    st.info(
        f"💡 On average, a country's rank moves **{avg_swing:.1f} places** between the "
        f"three methods for this indicator. The capped {lower}–{upper} scaling is the "
        "middle-ground choice that keeps the ranking stable without hiding the "
        "largest economies.",
    )
