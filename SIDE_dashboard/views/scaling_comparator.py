"""View 3: Scaling-method comparator (histograms + score stability)."""
from __future__ import annotations

import streamlit as st

from components import charts, ui
from core import chips_hierarchy as H
from core import rankings, scaling

DEFAULT_INDICATOR = "Median Mobile Download Speeds (Mbps)"

# The three possible pairs a user can pick from; stored as (method_a, method_b)
# where ``method_a`` is the x-axis (reference) and ``method_b`` the y-axis.
PAIR_OPTIONS = {
    f"{scaling.METHOD_LABELS[scaling.METHOD_FULL]} ↔ {scaling.METHOD_LABELS[scaling.METHOD_Z]}": (
        scaling.METHOD_FULL,
        scaling.METHOD_Z,
    ),
    f"{scaling.METHOD_LABELS[scaling.METHOD_FULL]} ↔ {scaling.METHOD_LABELS[scaling.METHOD_CAPPED]}": (
        scaling.METHOD_FULL,
        scaling.METHOD_CAPPED,
    ),
    f"{scaling.METHOD_LABELS[scaling.METHOD_CAPPED]} ↔ {scaling.METHOD_LABELS[scaling.METHOD_Z]}": (
        scaling.METHOD_CAPPED,
        scaling.METHOD_Z,
    ),
}
DEFAULT_PAIR = f"{scaling.METHOD_LABELS[scaling.METHOD_FULL]} ↔ {scaling.METHOD_LABELS[scaling.METHOD_Z]}"

SECTION_OPTIONS = ["📊 Individual indicator", "🧩 Composite CHIPS"]
DEFAULT_SECTION = SECTION_OPTIONS[1]


def _selected_pair() -> tuple[str, str]:
    label = st.radio(
        "Compare which two scalings?",
        list(PAIR_OPTIONS.keys()),
        index=list(PAIR_OPTIONS.keys()).index(DEFAULT_PAIR),
        key="sc_pair",
        horizontal=True,
    )
    return PAIR_OPTIONS[label]


def render(data, method=scaling.METHOD_CAPPED) -> None:
    ui.page_header(
        "⚖️ Scaling comparator",
        "Raw numbers are turned into 0–1 scores in different ways. Pick two "
        "methods and see how that choice changes individual indicators and the "
        "overall CHIPS composite — and which countries' scores are most "
        "sensitive to it.",
    )

    method_a, method_b = _selected_pair()

    section = st.radio(
        "Section",
        SECTION_OPTIONS,
        index=SECTION_OPTIONS.index(DEFAULT_SECTION),
        horizontal=True,
        label_visibility="collapsed",
        key="sc_section",
    )
    if section == SECTION_OPTIONS[0]:
        _indicator_section(data, method_a, method_b)
    else:
        _composite_section(data, method_a, method_b)


def _indicator_section(data, method_a: str, method_b: str) -> None:
    indicator = ui.indicator_selectbox(data, "Indicator", key="sc_indicator", default=DEFAULT_INDICATOR)
    if indicator is None:
        return

    if scaling.METHOD_CAPPED in (method_a, method_b):
        c1, c2 = st.columns(2)
        with c1:
            lower = st.slider("Lower cap percentile", 1, 49, 5, key="sc_lower",
                              help="Values below this percentile are pulled up to the cap.")
        with c2:
            upper = st.slider("Upper cap percentile", 51, 99, 95, key="sc_upper",
                              help="Values above this percentile are pulled down to the cap.")
    else:
        lower, upper = 5, 95

    lower_f, upper_f = lower / 100.0, upper / 100.0

    st.plotly_chart(
        charts.hist_panels(data, indicator, lower_f, upper_f, methods=[method_a, method_b]),
        width="stretch",
    )

    col_a, col_b = st.columns(2)
    for col, method in ((col_a, method_a), (col_b, method_b)):
        with col:
            st.markdown(f"**{scaling.METHOD_LABELS[method]}**")
            st.markdown({
                scaling.METHOD_FULL: "Simple and easy to explain, but a single extreme value can squash everyone else into a narrow band.",
                scaling.METHOD_CAPPED: "The robust choice for reporting: the scale ignores the extremes, so values stay stable.",
                scaling.METHOD_Z: "Measures how far each country sits from the mean in standard deviations, then maps to 0–1 — ranks match plain z-scores, but the values stay on the same scale as the others.",
            }[method])

    st.markdown("### How the scores change under each scaling")
    st.caption(
        "For a single indicator the two scalings are monotone transforms of the "
        "raw value, so they produce the **same country ordering** — the rank "
        "never differs between methods. What differs is the 0–1 score each "
        "country receives. (The composite CHIPS index in the Composite CHIPS "
        "section is different: it aggregates many differently-shaped transforms, "
        "so the two methods CAN change the overall ranking.)"
    )
    stability = rankings.score_stability_table(
        data, indicator, lower_f, upper_f, methods=[method_a, method_b]
    )

    left, right = st.columns([3, 2])
    with left:
        ui.show_table(
            stability[["Country", "value", method_a, method_b, "score_swing"]],
            column_config=ui.rank_column_config(data),
            height=400,
        )
    with right:
        st.subheader("Biggest movers")
        st.caption(f"Countries whose 0–1 score moves the most between {scaling.METHOD_SHORT_LABELS[method_a]} and {scaling.METHOD_SHORT_LABELS[method_b]}.")
        st.plotly_chart(charts.movers_bar(stability), width="stretch")

    avg_swing = float(stability["score_swing"].mean())
    st.info(
        f"💡 On average, a country's score swings by **{avg_swing:.2f} points** "
        f"between {scaling.METHOD_LABELS[method_a]} and "
        f"{scaling.METHOD_LABELS[method_b]} for this indicator.",
    )


def _composite_section(data, method_a: str, method_b: str) -> None:
    st.markdown("### Composite CHIPS: where the two scalings disagree")
    st.caption(
        "Each panel plots one level of the composite index: x = "
        f"**{scaling.METHOD_LABELS[method_a]}** score, y = "
        f"**{scaling.METHOD_LABELS[method_b]}** score. Countries on the dashed "
        "diagonal are unchanged by the scaling choice; the further a country "
        "sits from it, the more the choice matters. Dark markers diverge most, "
        "and the top divergers are labelled."
    )

    pillars, _ = H.resolve_hierarchy(data.numeric_df.columns)
    comp = rankings.composite_scaling_comparison(data, pillars, method_a, method_b)

    levels = ["chips"] + list(rankings.PILLAR_COLUMNS)
    level_labels = ["CHIPS composite"] + [f"{p.capitalize()} pillar" for p in rankings.PILLAR_COLUMNS]

    # Single source of truth for the level: the "Level" dropdown in the
    # divergence-details section below. The carousel arrows just move that
    # dropdown, so the scatter and the table always show the same comparison.
    current = st.session_state.get("sc_comp_level", "chips")
    if current not in levels:
        current = "chips"
    idx = levels.index(current)

    prev_col, mid_col, next_col = st.columns([1, 8, 1], vertical_alignment="center")
    with prev_col:
        if st.button("◀", key="sc_comp_prev"):
            st.session_state["sc_comp_level"] = levels[(idx - 1) % len(levels)]
            st.rerun()
    with mid_col:
        st.markdown(f"**{level_labels[idx]}** — {idx + 1} of {len(levels)}")
    with next_col:
        if st.button("▶", key="sc_comp_next"):
            st.session_state["sc_comp_level"] = levels[(idx + 1) % len(levels)]
            st.rerun()

    st.plotly_chart(
        charts.chips_scaling_scatter(comp, method_a, method_b, level=levels[idx], top_n=5),
        width="stretch",
    )

    _diverger_table(comp, method_a, method_b)


def _diverger_table(comp, method_a: str, method_b: str) -> None:
    st.markdown("#### Divergence details")
    level_names = ["chips"] + rankings.PILLAR_COLUMNS
    level_label = st.selectbox(
        "Level",
        level_names,
        format_func=lambda l: "Overall CHIPS" if l == "chips" else f"{l.capitalize()} pillar",
        key="sc_comp_level",
    )
    label_a = scaling.METHOD_SHORT_LABELS[method_a]
    label_b = scaling.METHOD_SHORT_LABELS[method_b]

    tab = comp.dropna(subset=[f"{level_label}_a", f"{level_label}_b"]).copy()
    tab = tab.sort_values(f"{level_label}_dscore", ascending=False)
    view = tab[
        [
            "Country",
            f"{level_label}_a",
            f"{level_label}_b",
            f"{level_label}_dscore",
            f"{level_label}_rank_a",
            f"{level_label}_rank_b",
            f"{level_label}_drank",
        ]
    ].copy()
    view.columns = [
        "Country",
        f"{label_a} score",
        f"{label_b} score",
        "Δ score",
        f"{label_a} rank",
        f"{label_b} rank",
        "Δ rank",
    ]
    cfg = {
        "Country": st.column_config.TextColumn("Country"),
        f"{label_a} score": st.column_config.NumberColumn(f"{label_a} score", format="%.3f"),
        f"{label_b} score": st.column_config.NumberColumn(f"{label_b} score", format="%.3f"),
        "Δ score": st.column_config.NumberColumn("Δ score", format="%.3f"),
        f"{label_a} rank": st.column_config.NumberColumn(f"{label_a} rank", format="%d"),
        f"{label_b} rank": st.column_config.NumberColumn(f"{label_b} rank", format="%d"),
        "Δ rank": st.column_config.NumberColumn("Δ rank", format="%d"),
    }
    ui.show_table(view, column_config=cfg, height=400)
