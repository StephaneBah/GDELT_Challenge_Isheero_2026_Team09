"""Séries temporelles Plotly — courbes simples, multi-pays, ruptures."""
from __future__ import annotations

from typing import Iterable, Mapping

import pandas as pd
import plotly.graph_objects as go


def line_with_breakpoints(
    series: pd.Series,
    breakpoints: Iterable[pd.Timestamp] = (),
    *,
    title: str = "",
    yaxis_title: str = "",
) -> go.Figure:
    """Trace une série temporelle avec des lignes verticales aux ruptures."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=series.index, y=series.values, mode="lines", name=yaxis_title or series.name)
    )
    for bp in breakpoints:
        fig.add_vline(x=bp, line_dash="dash", line_color="firebrick", opacity=0.5)
    fig.update_layout(title=title, yaxis_title=yaxis_title, xaxis_title="Date")
    return fig


def multi_line(
    series_by_label: Mapping[str, pd.Series],
    *,
    title: str = "",
    yaxis_title: str = "",
) -> go.Figure:
    """Plusieurs séries temporelles superposées (ex. par pays, par domaine)."""
    fig = go.Figure()
    for label, s in series_by_label.items():
        fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=label))
    fig.update_layout(title=title, yaxis_title=yaxis_title, xaxis_title="Date")
    return fig


def stacked_area(
    df: pd.DataFrame,
    *,
    date_col: str = "date",
    value_col: str = "value",
    category_col: str = "category",
    title: str = "",
) -> go.Figure:
    """Stacked area chart (ex. décomposition par EventRootCode ou par domaine)."""
    pivot = df.pivot_table(
        index=date_col, columns=category_col, values=value_col, aggfunc="sum"
    ).fillna(0)
    fig = go.Figure()
    for col in pivot.columns:
        fig.add_trace(
            go.Scatter(
                x=pivot.index,
                y=pivot[col],
                mode="lines",
                name=str(col),
                stackgroup="one",
            )
        )
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title=value_col)
    return fig
