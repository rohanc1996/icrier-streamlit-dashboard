"""Plotly chart builders used by the dashboard views.

Every function returns a ``plotly.graph_objects.Figure`` so the views stay thin.
Colours match the notebook (blue = full, orange = capped, green = log,
purple = z-score).
"""
from __future__ import annotations

import colorsys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components import country_names
from core import correlations, scaling

# World choropleths render a custom GeoJSON asset (``assets/world_india_official.geojson``)
# instead of Plotly's built-in country geometry.

_GEO_ASSET = Path(__file__).resolve().parent.parent / "assets" / "world_india_official.geojson"

def _official_world_geojson() -> dict:
    """Load the merged world GeoJSON (official India extent).

    Deliberately NOT process-cached: a long-running Streamlit server must always
    render the current asset on disk, never a stale in-memory copy of an older
    build. The file is ~1.3 MB; re-reading it per rerun is negligible next to
    the rest of the figure serialisation.
    """
    with open(_GEO_ASSET, encoding="utf-8") as fh:
        return json.load(fh)

SCALE_COLORS = {
    scaling.METHOD_FULL: "#4C78A8",
    scaling.METHOD_CAPPED: "#F58518",
    scaling.METHOD_LOG: "#54A24B",
    scaling.METHOD_Z: "#6A3D9A",
}
UP_COLOR = "#54A24B"      # green  - removing the country strengthens the link
DOWN_COLOR = "#E45756"    # red    - removing the country weakens the link

# Data-coverage colours mirror the leaderboard's badge: green = full
# (>= 90% of the CHIPS weight backed by values), amber = partial (>= 70%),
# red = sparse. Grey marks countries with no CHIPS score.
COVERAGE_COLORS = {"full": "#2E8B57", "partial": "#D69E2E", "sparse": "#C0392B"}
NO_SCORE_COLOR = "#C8CCD0"

# The race chart is a full-height figure that scrolls inside a fixed box (the
# view applies the box via a key-scoped CSS rule); its x-axis is drawn by a
# slim pinned strip below the box, so both must place ticks identically.
RACE_BOX_HEIGHT = 620
RACE_TICKS = [round(i * 0.1, 2) for i in range(11)]


def choropleth(data, indicator: str, selected_country: str | None = None) -> go.Figure:
    """World map coloured by one indicator. Clicking is handled by the view."""
    df = data.numeric_df[["Country", indicator]].copy()
    df = df.dropna(subset=[indicator]).copy()
    df["iso3"] = df["Country"].map(country_names.COUNTRY_TO_ISO3)
    df = df.dropna(subset=["iso3"]).copy().reset_index(drop=True)
    values = df[indicator].astype(float)

    selectedpoints = []
    if selected_country and selected_country in df["Country"].tolist():
        selectedpoints = df.index[df["Country"] == selected_country].tolist()

    fig = go.Figure(go.Choropleth(
        geojson=_official_world_geojson(),
        featureidkey="id",
        locations=df["iso3"],
        z=values,
        customdata=df[["Country"]],
        colorscale="Blues",
        colorbar=dict(title=data.friendly_names.get(indicator, indicator), len=0.7, tickformat=".3g"),
        hovertemplate="%{customdata[0]}<br><b>%{z:,.3g}</b><extra></extra>",
        marker=dict(line=dict(color="white", width=0.4)),
        selectedpoints=selectedpoints,
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.55)),
    ))
    fig.update_geos(projection_type="equirectangular", showframe=False,
                    showcountries=False, showcoastlines=True,
                    coastlinecolor="#cccccc")
    fig.update_layout(height=540, margin=dict(l=0, r=0, t=10, b=0),
                      geo=dict(bgcolor="rgba(0,0,0,0)"))
    return fig


def _coverage_color(row) -> str:
    """Line colour from a ``chips_table`` row: coverage badge, grey when unscored."""
    if pd.isna(row["chips"]):
        return NO_SCORE_COLOR
    if row["coverage"] >= 0.9:
        return COVERAGE_COLORS["full"]
    if row["coverage"] >= 0.7:
        return COVERAGE_COLORS["partial"]
    return COVERAGE_COLORS["sparse"]


def chips_race(scores: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    """Horizontal "race" chart of every country's CHIPS score.

    ``scores`` is the ``chips.chips_table()`` output. Countries are ordered
    best-first (rank #1 at the top); countries without a CHIPS score sit at
    the bottom in grey. Each country is drawn as a thin line in the colour of
    its leaderboard data badge and ends with the country's flag emoji (a text
    marker, so no image downloads or extra dependencies). Hovering any row
    shows a single box with the country's rank, CHIPS score and data coverage.

    Returns ``(figure, axis_strip)``: the full-height figure (scrollable in a
    fixed box by the view) and a slim strip that draws the x-axis ticks below
    it, so the axis stays visible without scrolling to the bottom of the box.
    """
    if scores is None or scores.empty:
        empty = go.Figure()
        return empty, go.Figure()

    scored = scores.dropna(subset=["chips"]).sort_values("chips", ascending=True)
    unscored = scores[scores["chips"].isna()]
    ordered = pd.concat([unscored, scored], ignore_index=True)

    labels = ordered["Country"].tolist()

    # One thin line per country, from 0 to its score, in its coverage colour.
    # A line trace per country keeps the colour per country. Hover is disabled
    # on the lines themselves: their two endpoints share a y, so hovermode="y"
    # would draw one box per endpoint (plus neighbours). Each row instead gets
    # a single invisible hover marker at the line end, so hovering anywhere
    # along the row shows exactly one box.
    fig = go.Figure()
    for _, row in ordered.iterrows():
        v = float(row["chips"]) if pd.notna(row["chips"]) else 0.0
        color = _coverage_color(row)
        rank_txt = f"#{int(row['rank'])}" if pd.notna(row["rank"]) else "—"
        chips_txt = f"{v:.3f}" if pd.notna(row["chips"]) else "no score"
        cov_txt = f"{row['coverage'] * 100:.0f}%"
        fig.add_trace(go.Scatter(
            x=[0.0, v],
            y=[row["Country"], row["Country"]],
            mode="lines",
            line=dict(color=color, width=3),
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[v], y=[row["Country"]],
            mode="markers",
            marker=dict(color="rgba(0,0,0,0)", size=10),
            customdata=[[str(row["Country"]), rank_txt, chips_txt, cov_txt]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "rank %{customdata[1]} · CHIPS <b>%{customdata[2]}</b> · "
                "coverage %{customdata[3]}<extra></extra>"
            ),
            showlegend=False,
        ))

    # Flag emoji pinned just past the line end (x = 0 for the unscored rows).
    flag_x = [v + 0.012 if pd.notna(v) else 0.0 for v in ordered["chips"]]
    fig.add_trace(go.Scatter(
        x=flag_x, y=labels, mode="text",
        text=[country_names.flag_emoji(c) for c in ordered["Country"]],
        textposition="middle left", textfont=dict(size=15),
        hoverinfo="skip",
    ))

    # Full height is kept for the scroll box. Tick labels live in the pinned
    # axis strip below the box; gridlines stay so values can be read against
    # the strip's ticks. b=0 puts the gridlines flush with the box bottom.
    # hovermode="y" + a tight hoverdistance = row-band hover: one box per row
    # (rows are ~22px apart, so 10px never matches two rows at once).
    fig.update_layout(
        height=max(500, 18 + 22 * len(ordered)),
        margin=dict(l=10, r=10, t=10, b=0),
        hovermode="y",
        hoverdistance=10,
        xaxis=dict(range=[0, 1.10], tickvals=RACE_TICKS, showticklabels=False, ticks=""),
        yaxis=dict(tickfont=dict(size=13)),
        showlegend=False,
    )

    # Pinned x-axis: a slim strip whose top-side axis line sits just below the
    # scroll box, using the same tick positions as the figure's gridlines.
    axis = go.Figure()
    axis.add_trace(go.Scatter(x=[None], y=[None], hoverinfo="skip", showlegend=False))
    axis.update_layout(
        height=30,
        margin=dict(l=10, r=10, t=0, b=0),
        xaxis=dict(
            range=[0, 1.10], tickvals=RACE_TICKS, tickformat=".2f",
            side="top", showgrid=False, showline=True, linecolor="#9AA0A6",
            ticks="outside", ticklen=4, tickfont=dict(size=11),
        ),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig, axis


def hist_panels(data, indicator: str, lower: float = 0.05, upper: float = 0.95) -> go.Figure:
    """Side-by-side histograms of the same indicator under each scaling."""
    methods = list(scaling.ALL_METHODS)
    titles = [
        f"{lower * 100:g}-{upper * 100:g} percentile capped" if m == scaling.METHOD_CAPPED
        else scaling.METHOD_LABELS[m]
        for m in methods
    ]
    fig = make_subplots(rows=1, cols=len(methods), subplot_titles=titles)
    for i, method in enumerate(methods, start=1):
        vals = scaling.transform_series(data.numeric_df[indicator], method, lower, upper).dropna()
        fig.add_trace(go.Histogram(
            x=vals, nbinsx=20, opacity=0.85,
            marker_color=SCALE_COLORS[method],
            name=scaling.METHOD_LABELS[method],
            showlegend=(i == 1),
            hovertemplate="Countries: %{y}<br>Score: %{x:.2f}<extra></extra>",
        ), row=1, col=i)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), barmode="overlay")
    for i in range(1, len(methods) + 1):
        fig.layout[f"xaxis{i}"].range = [0, 1]
        fig.layout[f"xaxis{i}"].tickformat = ".1f"
        fig.layout[f"yaxis{i}"].title.text = "Countries"
    return fig
# ---------------------------------------------------------------------------
# Scatter (one panel per scaling method, mirrors the notebook's run_theme code)
# ---------------------------------------------------------------------------

def _add_pearson_line(fig, xs, ys, row, col, showlegend):
    if len(xs) < 3 or xs.nunique() < 2 or ys.nunique() < 2:
        return
    slope, intercept = np.polyfit(xs, ys, 1)
    xline = np.linspace(xs.min(), xs.max(), 100)
    r = xs.corr(ys, method="pearson")
    fig.add_trace(go.Scatter(
        x=xline, y=slope * xline + intercept, mode="lines",
        name=f"Pearson {r:.2f}", legendgroup="trends", showlegend=showlegend,
        line=dict(color="#D62728", width=2),
        hovertemplate="Pearson trend line<extra></extra>",
    ), row=row, col=col)


def _add_spearman_line(fig, xs, ys, row, col, showlegend):
    """Rank-based regression mapped back to the original scale (from the notebook)."""
    if len(xs) < 3 or xs.nunique() < 2 or ys.nunique() < 2:
        return
    x_rank = xs.rank()
    y_rank = ys.rank()
    slope, intercept = np.polyfit(x_rank, y_rank, 1)
    x_sorted = xs.sort_values()
    y_sorted = ys.sort_values()
    xline = np.linspace(x_sorted.iloc[0], x_sorted.iloc[-1], 100)
    xline_rank = np.interp(xline, x_sorted.values, np.arange(1, len(x_sorted) + 1))
    pred_y_rank = slope * xline_rank + intercept
    yline = np.interp(pred_y_rank, np.arange(1, len(y_sorted) + 1), y_sorted.values)
    r = correlations.rank_corr(xs, ys)
    fig.add_trace(go.Scatter(
        x=xline, y=yline, mode="lines",
        name=f"Spearman {r:.2f}", legendgroup="trends", showlegend=showlegend,
        line=dict(color="#17BECF", width=2, dash="dash"),
        hovertemplate="Spearman (rank-based) trend line<extra></extra>",
    ), row=row, col=col)


def scatter_panels(
    data,
    x_col: str,
    y_col: str,
    highlight_countries: list[str] | None = None,
    lower: float = 0.05,
    upper: float = 0.95,
    exclude: list[str] | None = None,
) -> go.Figure:
    """One scatter panel per scaling method, with trendlines and highlighted countries."""
    highlight_countries = highlight_countries or []
    x_common, y_common, countries = correlations.prepare_pair(data, x_col, y_col)
    if exclude:
        mask = ~countries.isin(exclude)
        x_common, y_common, countries = x_common[mask], y_common[mask], countries[mask]

    methods = list(scaling.ALL_METHODS)
    titles = [
        f"{lower * 100:g}-{upper * 100:g} percentile capped" if m == scaling.METHOD_CAPPED
        else scaling.METHOD_LABELS[m]
        for m in methods
    ]
    fig = make_subplots(rows=1, cols=len(methods), subplot_titles=titles)
    for i, method in enumerate(scaling.ALL_METHODS, start=1):
        xs = scaling.transform_series(x_common, method, lower, upper).dropna()
        ys = scaling.transform_series(y_common, method, lower, upper).dropna()
        common = xs.index.intersection(ys.index)
        xs, ys = xs.loc[common], ys.loc[common]
        names = countries.loc[common].astype(str)
        first = i == 1

        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers", name="Countries",
            legendgroup="points", showlegend=first,
            marker=dict(color=SCALE_COLORS[method], size=7, opacity=0.7,
                        line=dict(width=0.5, color="white")),
            customdata=np.stack([names, np.round(xs.values, 3), np.round(ys.values, 3)], axis=-1),
            hovertemplate="%{customdata[0]}<br>x = %{customdata[1]}<br>y = %{customdata[2]}<extra></extra>",
        ), row=1, col=i)

        for j, country in enumerate(highlight_countries):
            pos = names.index[names == country]
            if pos.empty:
                continue
            xi, yi = xs.loc[pos[0]], ys.loc[pos[0]]
            fig.add_trace(go.Scatter(
                x=[xi], y=[yi], mode="markers+text",
                name=country, legendgroup="highlights", showlegend=first and j == 0,
                text=[country_names.short_name(country)], textposition="top center",
                textfont=dict(size=10, color="#111111"),
                marker=dict(color="#111111", size=9, line=dict(width=1, color="white")),
                customdata=np.stack([[country]]),
                hovertemplate="%{customdata[0]}<extra></extra>",
            ), row=1, col=i)

        _add_pearson_line(fig, xs, ys, row=1, col=i, showlegend=first)
        _add_spearman_line(fig, xs, ys, row=1, col=i, showlegend=first)

    fig.update_layout(
        height=470,
        margin=dict(l=10, r=10, t=110, b=10),
        legend=dict(orientation="h", yanchor="top", y=1.0,
                    xanchor="left", x=0, font=dict(size=11)),
    )
    # Panel headings sit in the top margin, just above each plot — never
    # overlapping the data. Their default position (paper y=1.0) crowds the
    # plot tops, so place each one explicitly above the plot area.
    plot_top = 1.0 - fig.layout.margin.t / fig.layout.height
    for ann in fig.layout.annotations:
        ann.update(y=plot_top + 0.015, yanchor="bottom", yshift=0)
    for i in range(1, len(methods) + 1):
        for axis in (f"xaxis{i}", f"yaxis{i}"):
            fig.layout[axis].range = [0, 1]
            fig.layout[axis].tickformat = ".1f"
    return fig
# ---------------------------------------------------------------------------
# Comparison & analysis charts
# ---------------------------------------------------------------------------

def _goodness_frame(data, indicators, lower=0.05, upper=0.95, method=scaling.METHOD_CAPPED) -> pd.DataFrame:
    """Scores (1.0 = best) for a set of indicators, one row per country."""
    df = data.numeric_df[["Country"]].copy()
    for indicator in indicators:
        sc = scaling.transform_series(data.numeric_df[indicator], method, lower, upper)
        if not data.higher_is_better.get(indicator, True):
            sc = 1.0 - sc
        df[indicator] = sc
    return df


def radar_chart(data, countries, indicators, lower=0.05, upper=0.95, method=scaling.METHOD_CAPPED) -> go.Figure:
    """Overlaid radar of scaled scores (1.0 = best) for 2-5 countries."""
    scores = _goodness_frame(data, indicators, lower, upper, method=method)
    theta = [data.friendly_names.get(i, i) for i in indicators]
    fig = go.Figure()
    for country in countries:
        if country not in scores["Country"].values:
            continue
        row = scores[scores["Country"] == country].iloc[0]
        fig.add_trace(go.Scatterpolar(
            r=row[indicators].astype(float).tolist(),
            theta=theta,
            fill="toself",
            name=country,
            hovertemplate="%{theta}<br>%{r:.2f}<extra></extra>",
        ))
    fig.update_layout(
        height=500, margin=dict(l=40, r=40, t=30, b=30),
        polar=dict(radialaxis=dict(range=[0, 1], tickvals=[0, 0.25, 0.5, 0.75, 1])),
    )
    return fig


def parallel_coords(data, countries, indicators, lower=0.05, upper=0.95, method=scaling.METHOD_CAPPED) -> go.Figure:
    """Parallel-coordinates view of the same scaled scores."""
    scores = _goodness_frame(data, indicators, lower, upper, method=method)
    if countries:
        scores = scores[scores["Country"].isin(countries)]
    dims = []
    for indicator in indicators:
        dims.append(dict(
            label=data.friendly_names.get(indicator, indicator),
            values=scores[indicator].astype(float),
            range=[0, 1],
        ))
    color_vals = scores[indicators[0]].astype(float) if indicators else scores.index
    fig = go.Figure(go.Parcoords(
        line=dict(color=color_vals, colorscale="Viridis", showscale=True),
        dimensions=dims,
    ))
    fig.update_layout(height=500, margin=dict(l=30, r=30, t=20, b=20))
    return fig


def profile_bars(data, country, indicators, lower=0.05, upper=0.95, method=scaling.METHOD_CAPPED) -> go.Figure:
    """Country score vs the world median for a set of indicators."""
    scores = _goodness_frame(data, indicators, lower, upper, method=method)
    rows = []
    for indicator in indicators:
        row = scores[scores["Country"] == country]
        if row.empty:
            continue
        col = scores[indicator].dropna()
        if len(col) < 3:
            continue
        cval = row[indicator].iloc[0]
        if pd.isna(cval):
            continue
        rows.append({
            "indicator": indicator,
            "country": cval,
            "world_median": float(col.median()),
        })
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("country", ascending=True)
    labels = [data.friendly_names.get(i, i) for i in df["indicator"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=df["world_median"], orientation="h",
                         name="World median", marker_color="#B0BEC5"))
    fig.add_trace(go.Bar(y=labels, x=df["country"], orientation="h",
                         name=country, marker_color="#F58518"))
    fig.update_layout(
        height=45 + 26 * len(labels), barmode="group",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[0, 1], title="Capped score (0-1, higher is better)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def leave_one_out_bar(loo_df: pd.DataFrame, base: float, method_label: str) -> go.Figure:
    """Bar chart of how much the correlation changes when each country is removed."""
    d = loo_df.sort_values("delta").copy()
    colors = np.where(d["delta"] >= 0, UP_COLOR, DOWN_COLOR)
    fig = go.Figure(go.Bar(
        x=d["delta"], y=d["country"], orientation="h",
        marker_color=colors,
        customdata=np.stack([d["country"], np.round(d["delta"], 3), d["n"]], axis=-1),
        hovertemplate="%{customdata[0]}<br>change = %{customdata[1]:+.3f}<br>countries used = %{customdata[2]}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="#333333", line_width=1)
    fig.update_layout(
        height=min(820, 40 + len(d) * 20),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title=f"Change in {method_label} when the country is removed (base = {base:.3f})",
    )
    return fig


def movers_bar(stability_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Horizontal bar of the countries whose score swings most across scalings.

    The four methods are monotone transforms of the raw value, so they preserve
    the same ordering (ranks never change). What differs is the 0-1 score; this
    bar highlights the countries whose score is most sensitive to the choice.
    """
    d = stability_df.head(top_n).iloc[::-1].copy()
    fig = go.Figure(go.Bar(
        x=d["score_swing"], y=d["Country"], orientation="h",
        marker_color="#4C78A8",
        customdata=np.stack([d["Country"], d["score_swing"]], axis=-1),
        hovertemplate="%{customdata[0]}<br>score swing = %{customdata[1]:.2f} points<extra></extra>",
    ))
    fig.update_layout(
        height=40 + len(d) * 26,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Max score swing between the four scaling methods",
    )
    return fig


# ---------------------------------------------------------------------------
# CHIPS composite index charts
# ---------------------------------------------------------------------------

PILLAR_HUES = {
    "CONNECT": 0.585,           # blue
    "HARNESS": 0.50,            # teal
    "INNOVATE": 0.09,           # orange
    "PROTECT": 0.99,            # red
    "SUSTAINABILITY": 0.375,    # green
}
MISSING_COLOR = "#cfd8dc"


def _cell_lightness(score: float | None) -> float:
    s = max(0.0, min(1.0, score)) if score is not None else 0.0
    return 0.82 - 0.47 * s


def _score_cell_color(pillar: str, score: float | None, status: str) -> str:
    if status != "present":
        return MISSING_COLOR
    hue = PILLAR_HUES.get(pillar, 0.585)
    r, g, b = colorsys.hls_to_rgb(hue, _cell_lightness(score), 0.68)
    return f"rgb({round(r * 255)}, {round(g * 255)}, {round(b * 255)})"


def _score_cell_text(score: float | None, status: str) -> str:
    if status != "present":
        return "#546e7a"
    return "#ffffff" if _cell_lightness(score) < 0.5 else "#123c63"


def chips_choropleth(chips_df: pd.DataFrame, selected_country: str | None = None) -> go.Figure:
    """World map coloured by the CHIPS score. Clicking is handled by the view."""
    df = chips_df.dropna(subset=["chips"]).copy()
    df["iso3"] = df["Country"].map(country_names.COUNTRY_TO_ISO3)
    df = df.dropna(subset=["iso3"]).reset_index(drop=True)

    selectedpoints = []
    if selected_country and selected_country in df["Country"].tolist():
        selectedpoints = df.index[df["Country"] == selected_country].tolist()

    fig = go.Figure(go.Choropleth(
        geojson=_official_world_geojson(),
        featureidkey="id",
        locations=df["iso3"],
        z=df["chips"].astype(float),
        customdata=df[["Country"]],
        colorscale="Blues",
        colorbar=dict(title="CHIPS score", len=0.7, tickformat=".2f"),
        hovertemplate="%{customdata[0]}<br><b>CHIPS %{z:.2f}</b><extra></extra>",
        marker=dict(line=dict(color="white", width=0.4)),
        selectedpoints=selectedpoints,
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=0.55)),
    ))
    fig.update_geos(projection_type="equirectangular", showframe=False,
                    showcountries=False, showcoastlines=True,
                    coastlinecolor="#cccccc")
    fig.update_layout(height=540, margin=dict(l=0, r=0, t=10, b=0),
                      geo=dict(bgcolor="rgba(0,0,0,0)"))
    return fig


def chips_treemap(rows: pd.DataFrame) -> go.Figure:
    """Treemap of the full CHIPS result tree for one country.

    ``rows`` comes from ``chips.tree_to_frame``.  Area = share of the CHIPS
    weight.  Colour = the pillar hue (one per pillar so the top-level blocks
    are easy to tell apart) shaded by score — darker = higher.  Missing and
    dropped cells are grey.  The frame carries a ``pillar`` column so every
    level of a pillar shares its hue.
    """
    rows = rows.copy()
    rows["label"] = rows["label"].replace("CHIPS composite", "CHIPS")
    rows["color"] = [_score_cell_color(p, s, t) for p, s, t in
                      zip(rows["pillar"], rows["score"], rows["status"])]
    rows["text_color"] = [_score_cell_text(s, t) for s, t in
                           zip(rows["score"], rows["status"])]
    custom = np.stack([
        np.round(rows["score"].fillna(-1.0), 3),
        np.round(rows["weight"] * 100, 2),
        rows["status"],
        rows["reason"].fillna(""),
    ], axis=-1)
    fig = go.Figure(go.Treemap(
        ids=rows["id"],
        parents=rows["parent"],
        labels=rows["label"],
        values=rows["weight"],
        branchvalues="total",
        marker=dict(colors=rows["color"], line=dict(color="white", width=0.8)),
        customdata=custom,
        texttemplate="%{label}<br>%{value:.1%}",
        textfont=dict(size=11, color=rows["text_color"]),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "weight: %{value:.1%} of CHIPS<br>"
            "score: %{customdata[0]}<br>"
            "status: %{customdata[2]}<br>"
            "%{customdata[3]}<extra></extra>"
        ),
    ))
    fig.update_layout(height=600, margin=dict(l=5, r=5, t=30, b=5))
    return fig


def coverage_scatter(df: pd.DataFrame) -> go.Figure:
    """CHIPS score vs weighted data coverage. Clicking is handled by the view."""
    d = df.dropna(subset=["chips"]).copy()
    fig = go.Figure(go.Scatter(
        x=d["coverage"] * 100,
        y=d["chips"],
        mode="markers",
        customdata=d[["Country", "indicators_present", "indicators_total"]],
        marker=dict(size=11, color=d["coverage"] * 100, colorscale="RdYlGn",
                    cmin=55, cmax=100, showscale=False,
                    line=dict(color="#333333", width=0.6)),
        hovertemplate=("%{customdata[0]}<br>"
                       "CHIPS <b>%{y:.2f}</b><br>"
                       "coverage %{x:.0f}%<br>"
                       "indicators %{customdata[1]}/%{customdata[2]}<extra></extra>"),
    ))
    median = d["chips"].median()
    fig.add_hline(y=median, line_dash="dot", line_color="#555555")
    fig.add_vline(x=70, line_dash="dot", line_color="#555555")
    fig.add_annotation(x=72, y=median, yshift=8, text="median CHIPS",
                       showarrow=False, font=dict(size=11, color="#555555"))
    fig.add_annotation(x=86, y=0.03, text="70% coverage",
                       showarrow=False, font=dict(size=11, color="#555555"))
    fig.update_layout(
        height=480, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="Data coverage (% of CHIPS weight backed by a value)", range=[50, 102]),
        yaxis=dict(title="CHIPS score (0-1)", range=[0, 1]),
    )
    return fig


def missingness_heatmap(codes: pd.DataFrame, reasons: pd.DataFrame) -> go.Figure:
    """Grid of sub-pillar status per country: green present, grey no data,
    red dropped (a rule removed the group despite partial data)."""
    fig = go.Figure(go.Heatmap(
        z=codes.values,
        x=codes.columns,
        y=codes.index,
        zmin=0,
        zmax=2,
        colorscale=[[0, "#2ca02c"], [0.5, "#9e9e9e"], [1, "#d62728"]],
        text=reasons.values,
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{text}<extra></extra>",
        colorbar=dict(tickvals=[0, 1, 2],
                      ticktext=["present", "no data", "dropped (rule)"],
                      len=0.6),
    ))
    fig.update_layout(
        height=max(560, 20 + 24 * len(codes)),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(tickangle=30),
    )
    fig.update_yaxes(autorange="reversed")
    return fig
