"""View 1: Interactive country explorer (map + profile + comparison)."""
from __future__ import annotations

import streamlit as st

from components import charts, country_names, ui
from core import rankings
from core.themes import HIGHLIGHT_COUNTRIES

DEFAULT_INDICATOR = "Median Mobile Download Speeds (Mbps)"

# Indicators used for headline metrics in the profile panel.
HEADLINE_INDICATORS = [
    "Median Mobile Download Speeds (Mbps)",
    "Number of Internet Users (absolute numbers)",
    "Number of smartphone users (million)",
    "Users of Digital Payments (in millions)",
    "Number of e-commerce users",
    "Total AI Private Investment in Millions",
    "Number of Start-ups",
    "Price of cheapest smartphone (PPP$)",
]

COMPARISON_INDICATORS = [
    "Median Mobile Download Speeds (Mbps)",
    "Price of cheapest smartphone (PPP$)",
    "Number of Internet Users (absolute numbers)",
    "Number of smartphone users (million)",
    "Users of Digital Payments (in millions)",
    "Number of e-commerce users",
    "Number of Start-ups",
    "Total AI Private Investment in Millions",
]


def _clicked_country(selection):
    """Extract the clicked country name from the plotly map selection event."""
    try:
        sel = getattr(selection, "selection", None)
        points = getattr(sel, "points", None)
        if not points:
            return None
        point = points[0]
        custom = getattr(point, "customdata", None)
        if custom is not None and len(custom) and custom[0]:
            return custom[0]
        location = getattr(point, "location", None)
        if location:
            return country_names.ISO3_TO_COUNTRY.get(location)
    except Exception:
        return None
    return None


def render(data) -> None:
    ui.page_header(
        "🌍 Country Explorer",
        "Click a country on the map to see how it performs on every indicator, "
        "then compare up to five countries side by side.",
    )
    ui.explainer(
        "👆",
        "Click any country on the map (or choose it in the box on the right) to "
        "open its profile. The map shows one indicator at a time — change it "
        "with the dropdown.",
    )

    col_map, col_pick = st.columns([3, 1])

    with col_map:
        indicator = ui.indicator_selectbox(data, "Colour the map by", key="ce_indicator", default=DEFAULT_INDICATOR)
        if indicator is None:
            return
        map_fig = charts.choropleth(data, indicator, st.session_state.get("selected_country"))
        selection = st.plotly_chart(map_fig, key="world_map", on_select="rerun", selection_mode="points")
        clicked = _clicked_country(selection)
        if clicked:
            st.session_state["selected_country"] = clicked

    with col_pick:
        st.subheader("Select a country")
        manual = st.selectbox("Search countries", data.country_list, key="ce_manual", label_visibility="collapsed")
        if st.button("📌 Open profile", key="ce_open", width="stretch"):
            st.session_state["selected_country"] = manual
        selected = st.session_state.get("selected_country")
        if selected:
            st.markdown(f"**Showing profile:** {selected}")
            if st.button("✕ Clear selection", key="ce_clear", width="stretch"):
                st.session_state.pop("selected_country", None)
                st.rerun()
        else:
            st.caption("No country selected yet — click the map or use the box.")

    selected = st.session_state.get("selected_country")
    if selected and selected in data.country_list:
        _profile_panel(data, selected)

    st.divider()
    _comparison_panel(data)
def _profile_panel(data, country: str) -> None:
    st.markdown(f"## 📋 Country profile — {country}")
    pr = rankings.profile_ranks(data, country)
    if pr.empty:
        st.warning("No usable data found for this country.")
        return

    metrics = []
    for ind in HEADLINE_INDICATORS:
        row = pr[pr["indicator"] == ind]
        if not row.empty:
            r = row.iloc[0]
            metrics.append((ind, r["value"], r["rank"], r["of"]))
    if metrics:
        cols = st.columns(len(metrics))
        for c, (ind, val, rank, n) in zip(cols, metrics):
            with c:
                st.metric(
                    label=data.friendly_names.get(ind, ind),
                    value=ui.fmt(val),
                    delta=f"rank #{int(rank)} / {int(n)}",
                )

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Ranking on every indicator")
        view = pr.copy()
        view["Indicator"] = view["indicator"].map(lambda i: data.friendly_names.get(i, i))
        view["Value"] = view["value"].map(ui.fmt)
        view["Percentile"] = view["percentile"].map(lambda p: f"{p:.0f}")
        ui.show_table(view[["rank", "Indicator", "Value", "Percentile"]], height=430)
    with right:
        st.subheader("💪 Strengths")
        for _, r in pr.head(5).iterrows():
            st.markdown(f"- **{data.friendly_names.get(r['indicator'], r['indicator'])}**: #{int(r['rank'])}/{int(r['of'])}")
        st.subheader("🎯 Areas to improve")
        for _, r in pr.tail(5).iloc[::-1].iterrows():
            st.markdown(f"- **{data.friendly_names.get(r['indicator'], r['indicator'])}**: #{int(r['rank'])}/{int(r['of'])}")

    with st.expander(f"📊 {country} vs the world median (capped score)"):
        fig = charts.profile_bars(data, country, HEADLINE_INDICATORS)
        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Not enough data to draw this chart.")


def _comparison_panel(data) -> None:
    st.markdown("## 🔄 Compare countries")
    ui.explainer(
        "🛰️",
        "Pick 2–5 countries and a few indicators. The radar (or parallel "
        "coordinates) shows the capped score — 0 to 1, higher is always better — "
        "so you can spot patterns at a glance.",
    )

    c1, c2 = st.columns(2)
    with c1:
        countries = st.multiselect(
            "Countries to compare",
            data.country_list,
            default=[c for c in HIGHLIGHT_COUNTRIES if c in data.country_list][:5],
            max_selections=5,
            key="ce_compare_countries",
        )
    with c2:
        indicators = st.multiselect(
            "Indicators",
            list(data.indicators),
            default=[i for i in COMPARISON_INDICATORS if i in data.indicators],
            key="ce_compare_indicators",
            format_func=lambda i: data.friendly_names.get(i, i),
            help="Scores use the capped 5–95 scaling, inverted where a low "
                 "value is better, so 1.0 always means 'best'.",
        )

    if len(countries) < 2:
        st.caption("Select at least 2 countries to see the comparison.")
        return
    if len(indicators) < 3:
        st.caption("Select at least 3 indicators for a meaningful chart.")
        return

    chart_type = st.radio("Chart type", ["Radar chart", "Parallel coordinates"], horizontal=True, key="ce_compare_type")
    if chart_type == "Radar chart":
        st.plotly_chart(charts.radar_chart(data, countries, indicators), width="stretch")
    else:
        st.plotly_chart(charts.parallel_coords(data, countries, indicators), width="stretch")

