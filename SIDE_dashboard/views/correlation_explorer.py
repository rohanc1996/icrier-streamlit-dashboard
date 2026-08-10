"""View 3: Correlation explorer (pick any two indicators)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components import charts, ui
from core import correlations
from core.themes import HIGHLIGHT_COUNTRIES, THEMES

DEFAULT_X = "Median Mobile Download Speeds (Mbps)"
DEFAULT_Y = "Total AI Private Investment in Millions"


def _verdict(table: pd.DataFrame) -> str:
    """Plain-language summary of how robust the correlation is."""
    row = {r["method"]: r for _, r in table.iterrows()}
    capped = row["capped"]
    diffs = [
        abs(capped["pearson"] - row["full"]["pearson"]),
        abs(capped["spearman"] - row["full"]["spearman"]),
        abs(capped["pearson"] - row["log"]["pearson"]),
        abs(capped["spearman"] - row["log"]["spearman"]),
    ]
    worst = max(diffs)
    sp = capped["spearman"]
    if worst < 0.05:
        msg = "All three scalings agree closely, so this relationship is **robust** — outliers are not driving it."
    elif worst < 0.15:
        msg = "The relationship is **moderately sensitive** to the scaling choice. A few extreme countries matter, but the overall picture holds."
    else:
        msg = "The relationship is **strongly influenced by a few extreme countries** — the correlation changes a lot depending on how the data is scaled. The capped (robust) and Spearman values are the most trustworthy."
    if sp is not None and not pd.isna(sp):
        direction = "positive" if sp > 0 else "negative"
        msg += f" The robust (capped, Spearman) correlation is **{sp:+.2f}**, a {direction} relationship."
    return msg


def render(data) -> None:
    ui.page_header(
        "🔬 Correlation explorer",
        "Test your own hypotheses: pick any two indicators and see how strongly "
        "they move together — and whether that link is robust.",
    )
    ui.explainer(
        "🧪",
        "You choose the two indicators. For each of the three scaling methods "
        "you get Pearson (linear) and Spearman (rank-based) correlations plus a "
        "trend line.",
    )

    with st.expander("🎯 Start from one of the five themes"):
        theme_name = st.selectbox("Theme", [t["name"] for t in THEMES], key="corr_theme")
        theme = next(t for t in THEMES if t["name"] == theme_name)
        st.caption(theme["description"])
        st.markdown("Suggested pairs:")
        for x, y in theme["pairs"]:
            st.markdown(f"- {data.friendly_names.get(x, x)}  **vs**  {data.friendly_names.get(y, y)}")
        if st.button("Load the first pair", key="corr_load"):
            st.session_state["corr_x"] = theme["pairs"][0][0]
            st.session_state["corr_y"] = theme["pairs"][0][1]
            st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        x_col = ui.indicator_selectbox(data, "X variable", key="corr_x", default=DEFAULT_X)
    with c2:
        y_col = ui.indicator_selectbox(data, "Y variable", key="corr_y", default=DEFAULT_Y)
    if x_col is None or y_col is None:
        return
    if x_col == y_col:
        st.warning("Pick two different indicators to compare.")
        return

    highlight = st.multiselect(
        "Highlight countries",
        data.country_list,
        default=[c for c in HIGHLIGHT_COUNTRIES if c in data.country_list],
        max_selections=8,
        key="corr_highlight",
    )

    st.plotly_chart(charts.scatter_3panel(data, x_col, y_col, highlight), width="stretch")

    table = correlations.compare_pair(data, x_col, y_col)
    view = table[["method_label", "n", "pearson", "spearman"]].rename(columns={"method_label": "method"})
    ui.show_table(view, column_config=ui.rank_column_config(data))

    st.info(_verdict(table))
