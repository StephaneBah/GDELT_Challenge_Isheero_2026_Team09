"""Sentiment multilingue avec xlm-roberta.

À utiliser pour valider AvgTone (signal grossier GDELT) sur un échantillon
de titres d'articles. Modèle local — aucun coût d'API.

Usage :
    from src.ml.sentiment import score_titles
    df = score_titles(titles)
"""
from __future__ import annotations

import logging
from typing import Iterable, List

import pandas as pd

logger = logging.getLogger(__name__)

# Modèle multilingue gratuit, classe en 1-5 étoiles (recodé en negatif/neutre/positif)
MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"


def _load_pipeline():
    """Lazy-load du pipeline HuggingFace (CPU par défaut)."""
    from transformers import pipeline

    logger.info("Chargement du modèle %s ...", MODEL_NAME)
    return pipeline("sentiment-analysis", model=MODEL_NAME, device=-1)


def score_titles(titles: Iterable[str], batch_size: int = 16) -> pd.DataFrame:
    """Renvoie un DataFrame {title, label, score, polarity} pour chaque titre.

    polarity : -1 (négatif fort), -0.5, 0, +0.5, +1 (positif fort).
    """
    titles = [t for t in titles if isinstance(t, str) and t.strip()]
    if not titles:
        return pd.DataFrame(columns=["title", "label", "score", "polarity"])

    pipe = _load_pipeline()
    out: List[dict] = []
    for i in range(0, len(titles), batch_size):
        batch = titles[i : i + batch_size]
        results = pipe(batch, truncation=True, max_length=256)
        for title, res in zip(batch, results):
            stars = int(res["label"].split()[0])  # "4 stars" -> 4
            polarity = (stars - 3) / 2  # 1->-1, 2->-0.5, 3->0, 4->0.5, 5->1
            out.append(
                {
                    "title": title,
                    "label": res["label"],
                    "score": res["score"],
                    "polarity": polarity,
                }
            )
    return pd.DataFrame(out)
