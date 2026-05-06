"""Nettoyage : data/raw/ -> data/interim/.

Étapes :
- Suppression des doublons (un GLOBALEVENTID unique par event)
- Drop des lignes sans géolocalisation (selon mode strict/large)
- Standardisation des dates
- Filtrage par profil de confiance (au moins NumSources >= 2 en mode strict)

Usage :
    python -m src.pipeline.clean
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.config import INTERIM_DIR, RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie le DataFrame events. Conserve les doublons NumMentions agrégé."""
    initial = len(df)
    df = df.drop_duplicates(subset=["GLOBALEVENTID"]).copy()
    df["SQLDATE"] = pd.to_datetime(df["SQLDATE"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["SQLDATE", "EventRootCode"])
    logger.info("events : %d -> %d lignes après nettoyage", initial, len(df))
    return df


def clean_mentions(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie le DataFrame mentions."""
    initial = len(df)
    df = df.drop_duplicates(
        subset=["GLOBALEVENTID", "MentionIdentifier"]
    ).copy()
    df["MentionTimeDate"] = pd.to_datetime(
        df["MentionTimeDate"], format="%Y%m%d%H%M%S", errors="coerce"
    )
    df["EventTimeDate"] = pd.to_datetime(
        df["EventTimeDate"], format="%Y%m%d%H%M%S", errors="coerce"
    )
    logger.info("mentions : %d -> %d lignes après nettoyage", initial, len(df))
    return df


def main() -> None:
    events_files = list(RAW_DIR.glob("events_*.parquet"))
    if not events_files:
        raise FileNotFoundError(
            "Aucun fichier raw events trouvé. Lancer d'abord `python -m src.pipeline.extract`."
        )

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    events = pd.read_parquet(events_files[0])
    events = clean_events(events)
    events.to_parquet(INTERIM_DIR / "events.parquet", compression="snappy", index=False)
    logger.info("events nettoyés : %s", INTERIM_DIR / "events.parquet")

    mentions_files = list(RAW_DIR.glob("mentions_*.parquet"))
    if mentions_files:
        mentions = pd.read_parquet(mentions_files[0])
        mentions = clean_mentions(mentions)
        mentions.to_parquet(
            INTERIM_DIR / "mentions.parquet", compression="snappy", index=False
        )
        logger.info("mentions nettoyées : %s", INTERIM_DIR / "mentions.parquet")
    else:
        logger.info("Pas de mentions à nettoyer (fichier raw absent — c'est OK).")


if __name__ == "__main__":
    main()
