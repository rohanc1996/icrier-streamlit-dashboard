"""Plotly chart builders used by the dashboard views.

Every function returns a ``plotly.graph_objects.Figure`` so the views stay thin.
Colours match the notebook (blue = full, orange = capped, green = log).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from components import country_names
from core import correlations, scaling

SCALE_COLORS = {
    scaling.METHOD_FULL: "#4C78A8",
    scaling.METHOD_CAPPED: "#F58518",
    scaling.METHOD_LOG: "#54A24B",
}
UP_COLOR = "#54A24B"      # green  - removing the country strengthens the link
DOWN_COLOR = "#E45756"    # red    - removing the country weakens the link


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
        locations=df["iso3"],
        z=values,
        locationmode="ISO-3",
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
                    showcoastlines=True, coastlinecolor="#cccccc")
    fig.update_layout(height=540, margin=dict(l=0, r=0, t=10, b=0),
                      geo=dict(bgcolor="rgba(0,0,0,0)"))
    return fig


def hist_3panel(data, indicator: str, lower: float = 0.05, upper: float = 0.95) -> go.Figure:
    """Three side-by-side histograms of the same indicator under each scaling."""
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Full-range min-max",
                        f"{lower * 100:g}-{upper * 100:g} percentile capped",
                        "Log-transformed min-max"),
    )
    for i, method in enumerate(scaling.ALL_METHODS, start=1):
        vals = scaling.transform_series(data.numeric_df[indicator], method, lower, upper).dropna()
        fig.add_trace(go.Histogram(
            x=vals, nbinsx=20, opacity=0.85,
            marker_color=SCALE_COLORS[method],
            name=scaling.METHOD_LABELS[method],
            showlegend=(i == 1),
            hovertemplate="Countries: %{y}<br>Score: %{x:.2f}<extra></extra>",
        ), row=1, col=i)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=50, b=10), barmode="overlay")
    for axis in ("xaxis", "xaxis2", "xaxis3"):
        fig.layout[axis].range = [0, 1]
        fig.layout[axis].tickformat = ".1f"
    for axis in ("yaxis", "yaxis2", "yaxis3"):
        fig.layout[axis].title.text = "Countries"
    return fig
# ---------------------------------------------------------------------------
# Scatter (3 panels, mirrors the notebook's run_theme plotting code)
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


def scatter_3panel(
    data,
    x_col: str,
    y_col: str,
    highlight_countries: list[str] | None = None,
    lower: float = 0.05,
    upper: float = 0.95,
    exclude: list[str] | None = None,
) -> go.Figure:
    """Full/capped/log scatter panels with trendlines and highlighted countries."""
    highlight_countries = highlight_countries or []
    x_common, y_common, countries = correlations.prepare_pair(data, x_col, y_col)
    if exclude:
        mask = ~countries.isin(exclude)
        x_common, y_common, countries = x_common[mask], y_common[mask], countries[mask]

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Full-range min-max",
                        f"{lower * 100:g}-{upper * 100:g} percentile capped",
                        "Log-transformed min-max"),
    )
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
    for axis in ("xaxis", "yaxis", "xaxis2", "yaxis2", "xaxis3", "yaxis3"):
        fig.layout[axis].range = [0, 1]
        fig.layout[axis].tickformat = ".1f"
    return fig
# ---------------------------------------------------------------------------
# Comparison & analysis charts
# ---------------------------------------------------------------------------

def _goodness_frame(data, indicators, lower=0.05, upper=0.95) -> pd.DataFrame:
    """Capped scores (1.0 = best) for a set of indicators, one row per country."""
    df = data.numeric_df[["Country"]].copy()
    for indicator in indicators:
        sc = scaling.transform_series(data.numeric_df[indicator], scaling.METHOD_CAPPED, lower, upper)
        if not data.higher_is_better.get(indicator, True):
            sc = 1.0 - sc
        df[indicator] = sc
    return df


def radar_chart(data, countries, indicators, lower=0.05, upper=0.95) -> go.Figure:
    """Overlaid radar of capped scores for 2-5 countries."""
    scores = _goodness_frame(data, indicators, lower, upper)
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


def parallel_coords(data, countries, indicators, lower=0.05, upper=0.95) -> go.Figure:
    """Parallel-coordinates view of the same capped scores."""
    scores = _goodness_frame(data, indicators, lower, upper)
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


def profile_bars(data, country, indicators, lower=0.05, upper=0.95) -> go.Figure:
    """Country score vs the world median for a set of indicators."""
    scores = _goodness_frame(data, indicators, lower, upper)
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
    """Horizontal bar of the countries whose rank swings most across scalings."""
    d = stability_df.head(top_n).iloc[::-1].copy()
    fig = go.Figure(go.Bar(
        x=d["max_swing"], y=d["Country"], orientation="h",
        marker_color="#4C78A8",
        customdata=np.stack([d["Country"], d["max_swing"]], axis=-1),
        hovertemplate="%{customdata[0]}<br>rank swing = %{customdata[1]} places<extra></extra>",
    ))
    fig.update_layout(
        height=40 + len(d) * 26,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Max rank swing between the three scaling methods",
    )
    return fig


# ---------------------------------------------------------------------------
# CHIPS composite index charts
# ---------------------------------------------------------------------------

CHIPS_TREEMAP_SCALE = [
    [0.0, "#cfd8dc"],   # missing / dropped cells
    [0.001, "#cfd8dc"],
    [0.002, "#f7fbff"],
    [0.25, "#c6dbef"],
    [0.5, "#6baed6"],
    [0.75, "#2171b5"],
    [1.0, "#08306b"],
]


def chips_choropleth(chips_df: pd.DataFrame, selected_country: str | None = None) -> go.Figure:
    """World map coloured by the CHIPS score. Clicking is handled by the view."""
    df = chips_df.dropna(subset=["chips"]).copy()
    df["iso3"] = df["Country"].map(country_names.COUNTRY_TO_ISO3)
    df = df.dropna(subset=["iso3"]).reset_index(drop=True)

    selectedpoints = []
    if selected_country and selected_country in df["Country"].tolist():
        selectedpoints = df.index[df["Country"] == selected_country].tolist()

    fig = go.Figure(go.Choropleth(
        locations=df["iso3"],
        z=df["chips"].astype(float),
        locationmode="ISO-3",
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
                    showcoastlines=True, coastlinecolor="#cccccc")
    fig.update_layout(height=540, margin=dict(l=0, r=0, t=10, b=0),
                      geo=dict(bgcolor="rgba(0,0,0,0)"))
    return fig


def chips_treemap(rows: pd.DataFrame) -> go.Figure:
    """Treemap of one country's full CHIPS result tree.

    ``rows`` comes from ``chips.tree_to_frame``.  Cell colour = score (blue
    ramp); missing/dropped cells are grey.  Area = share of the CHIPS weight.
    """
    rows = rows.copy()
    rows["label"] = rows["label"].replace("CHIPS composite", "CHIPS")
    present = rows["status"] == "present"
    rows["color"] = np.where(present, rows["score"].fillna(0.0) * 0.998 + 0.002, 0.0)
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
        marker=dict(colors=rows["color"], colorscale=CHIPS_TREEMAP_SCALE,
                    line=dict(color="white", width=0.8)),
        customdata=custom,
        texttemplate="%{label}<br>%{value:.1%}",
        textfont=dict(size=11, color="#123c63"),
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


def reweight_bars(rw_df: pd.DataFrame) -> go.Figure:
    """Nominal vs effective sub-pillar weights (missing siblings redistribute)."""
    d = rw_df[rw_df["status"] == "present"].copy()
    if d.empty:
        return None
    d = d.sort_values("label")
    d["inflation"] = d["effective"] - d["nominal"]
    colors = np.where(d["inflation"] >= 0, "#2171b5", "#d62728")
    fig = go.Figure(go.Bar(
        x=d["inflation"],
        y=d["label"],
        orientation="h",
        marker_color=colors,
        customdata=np.stack([
            np.round(d["nominal"], 3), np.round(d["effective"], 3),
            np.round(d["score"].fillna(-1.0), 3),
        ], axis=-1),
        hovertemplate=("%{y}<br>"
                       "nominal %{customdata[0]} → effective %{customdata[1]}"
                       "<br>score %{customdata[2]}<extra></extra>"),
    ))
    fig.add_vline(x=0, line_color="#333333", line_width=1)
    fig.update_layout(
        height=min(700, 40 + 24 * len(d)),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Effective − nominal weight within the pillar (missing siblings' weight is redistributed)",
    )
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


def rank_band_chart(band_df: pd.DataFrame) -> go.Figure:
    """Range bars: where each country's rank would land if its missing data
    were filled optimistically (0.75) vs pessimistically (0.25)."""
    d = band_df.copy()
    d["width"] = d["rank_max"] - d["rank_min"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d["width"],
        y=d["Country"],
        orientation="h",
        base=d["rank_min"],
        marker_color="rgba(33, 113, 181, 0.35)",
        customdata=np.stack([d["rank_min"], d["rank_max"], np.round(d["chips"], 3)], axis=-1),
        hovertemplate=("%{y}<br>rank could be %{customdata[0]}–%{customdata[1]}"
                       "<br>actual CHIPS %{customdata[2]}<extra></extra>"),
        name="Possible rank range",
    ))
    fig.add_trace(go.Scatter(
        x=d["rank"],
        y=d["Country"],
        mode="markers",
        marker=dict(size=8, color="#d62728", line=dict(color="white", width=1)),
        hovertemplate="%{y}<br>actual rank <b>%{x}</b><extra></extra>",
        name="Actual rank",
    ))
    fig.update_layout(
        height=min(1000, 40 + 20 * len(d)),
        margin=dict(l=10, r=10, t=10, b=10),
        barmode="overlay",
        xaxis=dict(title="Rank (1 = best)", autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig



