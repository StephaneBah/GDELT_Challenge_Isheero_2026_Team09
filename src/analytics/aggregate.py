"""Agrégations pures sur DataFrames events / stories.

Toutes les fonctions sont pures : elles ne mutent pas l'entrée et ne lisent
aucun fichier. Elles s'appliquent indifféremment à un DataFrame d'events ou
de stories tant que les colonnes attendues sont présentes.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd


def by_admin1(
    df: pd.DataFrame,
    value_col: str = "n_events",
    *,
    country_col: str = "ActionGeo_CountryCode",
    admin1_col: str = "dept_normalized",
    agg: str = "sum",
) -> pd.DataFrame:
    """Agrège par département (admin1).

    Args:
        df: DataFrame events ou stories enrichi.
        value_col: colonne à agréger (par défaut, on compte les lignes).
        country_col: colonne pays.
        admin1_col: colonne département (normalisé).
        agg: fonction d'agrégation (`sum`, `mean`, `count`, `nunique`...).

    Returns:
        DataFrame [country, admin1, value].
    """
    grouped = df.groupby([country_col, admin1_col], dropna=False)
    if value_col == "n_events":
        out = grouped.size().reset_index(name="n_events")
    else:
        out = grouped[value_col].agg(agg).reset_index()
    return out


def by_country(
    df: pd.DataFrame,
    value_col: str = "n_events",
    *,
    country_col: str = "ActionGeo_CountryCode",
    agg: str = "sum",
) -> pd.DataFrame:
    """Agrège par pays."""
    grouped = df.groupby(country_col, dropna=False)
    if value_col == "n_events":
        out = grouped.size().reset_index(name="n_events")
    else:
        out = grouped[value_col].agg(agg).reset_index()
    return out


def time_series(
    df: pd.DataFrame,
    *,
    date_col: str = "SQLDATE",
    value_col: str | None = None,
    freq: str = "D",
    agg: str = "sum",
    weight_col: str | None = None,
) -> pd.Series:
    """Construit une série temporelle.

    Args:
        df: DataFrame events ou stories.
        date_col: colonne datetime.
        value_col: si None, compte les lignes ; sinon agrège.
        freq: fréquence pandas (`D`, `W`, `M`).
        agg: fonction d'agrégation.
        weight_col: si fourni, calcule une moyenne pondérée par ce poids.

    Returns:
        pd.Series indexée par date.
    """
    s = df.set_index(date_col)
    if weight_col is not None and value_col is not None:
        weighted = (s[value_col] * s[weight_col]).resample(freq).sum()
        weights = s[weight_col].resample(freq).sum().replace(0, pd.NA)
        return (weighted / weights).rename(value_col)
    if value_col is None:
        return s.resample(freq).size().rename("count")
    return s[value_col].resample(freq).agg(agg)


def top_n(
    df: pd.DataFrame,
    group_col: str,
    value_col: str = "NumMentions",
    *,
    n: int = 10,
    agg: str = "sum",
) -> pd.DataFrame:
    """Top-N selon une colonne de poids."""
    out = df.groupby(group_col, dropna=False)[value_col].agg(agg).reset_index()
    return out.sort_values(value_col, ascending=False).head(n).reset_index(drop=True)


def co_occurrence(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    *,
    weight_col: str = "NumMentions",
    drop_self: bool = True,
) -> pd.DataFrame:
    """Compte les co-occurrences pondérées entre deux colonnes (ex. acteurs)."""
    sub = df[[col_a, col_b, weight_col]].dropna()
    if drop_self:
        sub = sub[sub[col_a] != sub[col_b]]
    out = (
        sub.groupby([col_a, col_b])[weight_col]
        .sum()
        .reset_index()
        .rename(columns={weight_col: "weight"})
    )
    return out.sort_values("weight", ascending=False).reset_index(drop=True)


def filter_period(
    df: pd.DataFrame,
    *,
    date_col: str = "SQLDATE",
    date_from: pd.Timestamp | str | None = None,
    date_to: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Filtre un DataFrame sur une fenêtre temporelle (inclusive sur les deux bornes)."""
    out = df
    if date_from is not None:
        out = out[out[date_col] >= pd.to_datetime(date_from)]
    if date_to is not None:
        out = out[out[date_col] <= pd.to_datetime(date_to)]
    return out


def split_periods(
    df: pd.DataFrame,
    pivot: pd.Timestamp | str,
    *,
    date_col: str = "SQLDATE",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Découpe un DataFrame en deux selon une date pivot.

    Utile pour comparer pré/post un événement (ex. rupture CEDEAO/AES juillet 2023).
    Retourne (avant, apres). La date pivot est incluse dans `apres`.
    """
    pivot_ts = pd.to_datetime(pivot)
    return df[df[date_col] < pivot_ts], df[df[date_col] >= pivot_ts]


def confidence_filter(
    df: pd.DataFrame,
    *,
    tier: str = "all",
    tier_col: str = "confidence_tier",
) -> pd.DataFrame:
    """Filtre selon le tier de confiance (cf. doctrine, principe 2)."""
    if tier == "all":
        return df
    if tier_col not in df.columns:
        return df
    return df[df[tier_col] == tier]


def domain_filter(
    df: pd.DataFrame,
    domains: Iterable[str],
    *,
    domain_col: str = "risk_domain",
) -> pd.DataFrame:
    """Filtre par domaine(s) de risque (cf. doctrine, principe 3)."""
    domains = tuple(domains)
    if not domains:
        return df
    return df[df[domain_col].isin(domains)]
