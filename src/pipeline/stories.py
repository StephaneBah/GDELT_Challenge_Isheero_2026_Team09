"""Clustering events -> stories.

Cf. doctrine, principe 1 (story-as-unit). Une story regroupe plusieurs events
relatant le même fait. Méthode initiale (à raffiner par le ML Engineer) :

- Clé de regroupement : (date_jour, EventRootCode, ActionGeo_ADM1Code, top acteurs)
- Optionnel : embeddings sentence-transformers sur titres pour merger plus fin

Usage :
    python -m src.pipeline.stories
"""
from __future__ import annotations

import logging

import pandas as pd

from src.config import PROCESSED_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def cluster_to_stories(events: pd.DataFrame) -> pd.DataFrame:
    """Première version : clustering rule-based simple.

    Une story = un même jour + même root code + même admin1 + même paire d'acteurs.
    Le ML Engineer peut ensuite remplacer cette logique par BERTopic ou
    DBSCAN sur embeddings de titres pour un regroupement plus fin.
    """
    df = events.copy()
    df["story_key"] = (
        df["SQLDATE"].dt.strftime("%Y%m%d")
        + "|"
        + df["EventRootCode"].astype(str)
        + "|"
        + df["ActionGeo_ADM1Code"].fillna("UNK").astype(str)
        + "|"
        + df["Actor1Code"].fillna("UNK").astype(str)
        + "|"
        + df["Actor2Code"].fillna("UNK").astype(str)
    )

    stories = (
        df.groupby("story_key")
        .agg(
            story_date=("SQLDATE", "min"),
            event_root_code=("EventRootCode", "first"),
            risk_domain=("risk_domain", "first"),
            confidence_tier=("confidence_tier", "first"),
            country_code=("ActionGeo_CountryCode", "first"),
            adm1_code=("ActionGeo_ADM1Code", "first"),
            dept_normalized=("dept_normalized", "first"),
            actor1=("Actor1Name", "first"),
            actor2=("Actor2Name", "first"),
            n_events=("GLOBALEVENTID", "count"),
            n_mentions=("NumMentions", "sum"),
            n_sources=("NumSources", "sum"),
            avg_tone=("AvgTone", "mean"),
            avg_goldstein=("GoldsteinScale", "mean"),
            sample_url=("SOURCEURL", "first"),
        )
        .reset_index()
    )
    logger.info(
        "Clustering : %d events -> %d stories (ratio %.1fx)",
        len(events),
        len(stories),
        len(events) / max(len(stories), 1),
    )
    return stories


def main() -> None:
    events = pd.read_parquet(PROCESSED_DIR / "events_enriched.parquet")
    stories = cluster_to_stories(events)
    out = PROCESSED_DIR / "stories.parquet"
    stories.to_parquet(out, compression="snappy", index=False)
    logger.info("Stories écrites : %s", out)


if __name__ == "__main__":
    main()
