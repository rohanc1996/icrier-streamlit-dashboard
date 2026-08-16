"""View 5: Outlier / leave-one-out explorer."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts, ui
from core import correlations, scaling

DEFAULT_X = "Median Mobile Download Speeds (Mbps)"
DEFAULT_Y = "Total AI Private Investment in Millions"


def render(data, method=scaling.METHOD_CAPPED) -> None:
    ui.page_header(
        "🕵️ Outlier explorer",
        "Which countries are pulling the relationship one way or the other? "
        "Remove a country and watch the correlation move.",
    )
    ui.explainer(
        "🔍",
        "For any pair of indicators this page removes each country one at a "
        "time and measures how much the correlation changes. A big bar means "
        "that country strongly influences the link.",
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        x_col = ui.indicator_selectbox(data, "X variable", key="oo_x", default=DEFAULT_X)
    with c2:
        y_col = ui.indicator_selectbox(data, "Y variable", key="oo_y", default=DEFAULT_Y)
    with c3:
        method_choice = st.radio("Correlation", ["Spearman (robust)", "Pearson"], key="oo_method")
    if x_col is None or y_col is None:
        return
    if x_col == y_col:
        st.warning("Pick two different indicators to compare.")
        return

    corr_method = "spearman" if method_choice == "Spearman (robust)" else "pearson"
    corr_label = "Spearman" if corr_method == "spearman" else "Pearson"

    loo, base = correlations.leave_one_out(data, x_col, y_col, corr_method=corr_method, scaling_method=method)
    if loo.empty:
        st.warning("Not enough overlapping data to run the leave-one-out analysis.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{corr_label} correlation (all countries)", f"{base:.3f}")
    c2.metric("Largest single influence", f"{loo.iloc[0]['delta']:+.3f}", delta=f"{loo.iloc[0]['country']}")
    c3.metric("Countries in the analysis", f"{len(loo)}")

    st.plotly_chart(charts.leave_one_out_bar(loo, base, corr_label), width="stretch")

    top = loo.head(3)
    parts = []
    for _, r in top.iterrows():
        action = "weaken" if r["delta"] < 0 else "strengthen"
        parts.append(f"**{r['country']}** ({r['delta']:+.3f}, tends to {action} the link)")
    st.markdown("### 🎯 The three most influential countries")
    st.markdown(" — ".join(parts))

    st.markdown("### 🧹 Remove countries and recalculate")
    excluded = st.multiselect(
        "Exclude these countries",
        data.country_list,
        key="oo_exclude",
        help="The scatter panels and the correlation update live.",
    )
    colA, colB = st.columns([1, 3])
    with colA:
        corr_excl, n = correlations.corr_with_exclusions(data, x_col, y_col, corr_method=corr_method, excluded=excluded, scaling_method=method)
        st.metric(f"{corr_label} without excluded", f"{corr_excl:.3f}" if not pd.isna(corr_excl) else "—")
        st.metric("Countries used", f"{n}")
        if excluded and st.button("Reset exclusions", key="oo_reset"):
            st.session_state["oo_exclude"] = []
            st.rerun()
    with colB:
        st.plotly_chart(charts.scatter_panels(data, x_col, y_col, exclude=excluded), width="stretch")
