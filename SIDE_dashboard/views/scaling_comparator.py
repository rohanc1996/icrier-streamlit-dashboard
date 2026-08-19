"""View 3: Scaling-method comparator (histograms + score stability)."""
from __future__ import annotations

import streamlit as st

from components import charts, ui
from core import rankings, scaling

DEFAULT_INDICATOR = "Median Mobile Download Speeds (Mbps)"


def render(data, method=scaling.METHOD_CAPPED) -> None:
    ui.page_header(
        "⚖️ Scaling comparator",
        "Raw numbers are turned into 0–1 scores in four different ways. "
        "This page shows how that choice changes the picture — and which "
        "countries' scores are most sensitive to it.",
    )
    ui.explainer(
        "🧭",
        "Use the sliders to change the cap window. Watch the middle histogram "
        "and the score table below update live.",
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

    st.plotly_chart(charts.hist_panels(data, indicator, lower_f, upper_f), width="stretch")

    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.markdown("**Full-range min-max**")
        st.markdown("Simple and easy to explain, but a single extreme value can squash everyone else into a narrow band.")
    with col_b:
        st.markdown(f"**{lower}–{upper} percentile capped**")
        st.markdown("The robust choice for reporting: the scale ignores the extremes, so values stay stable.")
    with col_c:
        st.markdown("**Log-transformed min-max**")
        st.markdown("Compresses the upper tail to reflect percentage-like differences, but is less intuitive.")
    with col_d:
        st.markdown("**Z-score (standardized)**")
        st.markdown("Measures how far each country sits from the mean in standard deviations, then maps to 0–1 — ranks match plain z-scores, but the values stay on the same scale as the others.")

    st.markdown("### How the scores change under each scaling")
    st.caption(
        "The four scalings are monotone transforms of the raw value, so they all "
        "produce the **same country ordering** — the rank never differs between "
        "methods. What differs is the 0–1 score: the swing column shows how much "
        "each country's score moves around with the scaling choice."
    )
    stability = rankings.score_stability_table(data, indicator, lower_f, upper_f)

    left, right = st.columns([3, 2])
    with left:
        ui.show_table(
            stability[["Country", "value"] + list(scaling.ALL_METHODS) + ["score_swing"]],
            column_config=ui.rank_column_config(data),
            height=400,
        )
    with right:
        st.subheader("Biggest movers")
        st.caption("Countries whose 0–1 score moves the most when the scaling method changes.")
        st.plotly_chart(charts.movers_bar(stability), width="stretch")

    avg_swing = float(stability["score_swing"].mean())
    st.info(
        f"💡 On average, a country's score swings by **{avg_swing:.2f} points** between the "
        f"four methods for this indicator. The capped {lower}–{upper} scaling is the "
        "middle-ground choice that keeps values stable without hiding the largest "
        "economies.",
    )
