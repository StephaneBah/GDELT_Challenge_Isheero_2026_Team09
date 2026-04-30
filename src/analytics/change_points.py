"""Détection de points de bascule (PELT).

Primitive analytique pure : prend une série temporelle, renvoie une liste de
dates de rupture. Aucune dépendance à un modèle entraîné. Utilisable depuis
toute question (en pratique, surtout Q2 — le ton).
"""
from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def detect_breakpoints(
    series: pd.Series,
    *,
    penalty: float = 10.0,
    min_size: int = 7,
    model: str = "rbf",
) -> List[pd.Timestamp]:
    """Détecte les points de bascule dans une série temporelle.

    Args:
        series: série indexée par date, valeur = signal (ex. ton moyen).
        penalty: pénalité PELT (plus haute = moins de ruptures).
        min_size: taille minimale de segment (en pas de temps).
        model: noyau de coût (`rbf`, `l1`, `l2`).

    Returns:
        Liste des dates de rupture détectées.
    """
    import ruptures as rpt

    if series.isna().all():
        return []

    values = series.fillna(method="ffill").fillna(method="bfill").values
    if len(values) < 2 * min_size:
        return []

    algo = rpt.Pelt(model=model, min_size=min_size).fit(values)
    breakpoints_idx = algo.predict(pen=penalty)
    breakpoints_idx = [i for i in breakpoints_idx if i < len(series)]
    breakpoints = [series.index[i] for i in breakpoints_idx]
    logger.info(
        "Détectés : %d points de bascule sur série de %d points",
        len(breakpoints),
        len(series),
    )
    return breakpoints


def smooth_tone(
    df: pd.DataFrame,
    *,
    date_col: str = "SQLDATE",
    tone_col: str = "AvgTone",
    weight_col: str = "NumMentions",
    window: str = "7D",
) -> pd.Series:
    """Calcule le ton lissé pondéré, fenêtre roulante."""
    sub = df[[date_col, tone_col, weight_col]].dropna().copy()
    sub["weighted"] = sub[tone_col] * sub[weight_col]
    daily = sub.groupby(date_col).agg(
        weighted=("weighted", "sum"),
        n=(weight_col, "sum"),
    )
    daily["tone"] = daily["weighted"] / daily["n"].replace(0, np.nan)
    return daily["tone"].rolling(window=window, min_periods=1).mean()
