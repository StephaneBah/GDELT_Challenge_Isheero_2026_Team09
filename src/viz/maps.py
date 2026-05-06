"""Cartes Plotly — choroplèthe Bénin et scatter géographique.

Le shapefile officiel des départements béninois doit être placé dans
`data/external/benin_admin1.geojson` pour que `choropleth_benin` fonctionne.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import EXTERNAL_DIR

BENIN_ADMIN1_GEOJSON = EXTERNAL_DIR / "benin_admin1.geojson"


def _load_benin_geojson() -> dict | None:
    """Charge le geojson des départements béninois si disponible."""
    if not BENIN_ADMIN1_GEOJSON.exists():
        return None
    return json.loads(BENIN_ADMIN1_GEOJSON.read_text(encoding="utf-8"))


def choropleth_benin(
    df: pd.DataFrame,
    *,
    dept_col: str = "dept_normalized",
    value_col: str = "n_events",
    title: str = "",
    color_scale: str = "Reds",
    feature_id_key: str = "properties.dept_name",
) -> go.Figure:
    """Choroplèthe par département béninois.

    Args:
        df: DataFrame [dept_normalized, value].
        dept_col: colonne département dans `df`.
        value_col: colonne valeur à colorier.
        title: titre de la figure.
        color_scale: palette Plotly.
        feature_id_key: chemin vers le nom de département dans le geojson.

    Returns:
        Figure Plotly. Si le geojson est absent, renvoie un bar chart fallback.
    """
    geojson = _load_benin_geojson()
    if geojson is None:
        # Fallback : bar chart par département
        fig = px.bar(
            df.sort_values(value_col, ascending=False),
            x=dept_col,
            y=value_col,
            title=title or "Par département (fallback — geojson manquant)",
            color=value_col,
            color_continuous_scale=color_scale,
        )
        fig.add_annotation(
            text="ℹ️ Charger data/external/benin_admin1.geojson pour la carte",
            xref="paper",
            yref="paper",
            x=0.5,
            y=1.05,
            showarrow=False,
        )
        return fig

    # Extraire la clé de feature depuis le chemin (ex: "properties.dept_name" → "dept_name")
    feat_key = feature_id_key.split(".")[-1]
    all_depts = [feat["properties"][feat_key] for feat in geojson["features"]]

    # Compléter avec les 12 départements (0 pour ceux sans événements)
    full = pd.DataFrame({dept_col: all_depts})
    if value_col in df.columns:
        full = full.merge(df[[dept_col, value_col]], on=dept_col, how="left")
        full[value_col] = full[value_col].fillna(0).astype(int)
    else:
        full[value_col] = 0

    # choropleth_mapbox : zoom et centre explicites → fiable pour les petits pays.
    # carto-positron est gratuit (pas de token Mapbox requis) et sobre visuellement.
    # Centre Bénin ≈ 9.3°N, 2.3°E · zoom 6 = pays entier visible.
    fig = px.choropleth_mapbox(
        full,
        geojson=geojson,
        locations=dept_col,
        color=value_col,
        featureidkey=feature_id_key,
        color_continuous_scale=color_scale,
        mapbox_style="carto-positron",
        zoom=6,
        center={"lat": 9.3, "lon": 2.3},
        opacity=0.75,
        title=title,
        hover_name=dept_col,
        labels={value_col: "Incidents sécuritaires"},
    )
    fig.update_layout(margin={"r": 0, "t": 40, "l": 0, "b": 0}, height=500)
    return fig


def scatter_geo(
    df: pd.DataFrame,
    *,
    lat_col: str = "ActionGeo_Lat",
    lon_col: str = "ActionGeo_Long",
    size_col: str = "NumMentions",
    color_col: str = "AvgTone",
    hover_col: str | None = None,
    title: str = "",
    scope: str = "africa",
) -> go.Figure:
    """Scatter géographique : un point par event/story."""
    sub = df.dropna(subset=[lat_col, lon_col]).copy()
    return px.scatter_geo(
        sub,
        lat=lat_col,
        lon=lon_col,
        size=size_col if size_col in sub.columns else None,
        color=color_col if color_col in sub.columns else None,
        hover_name=hover_col,
        scope=scope,
        title=title,
    )
