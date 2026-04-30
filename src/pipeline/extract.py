"""Extraction one-shot des événements GDELT sur 12 mois et 3 pays.

Snapshot figé : Bénin (BC) + Burkina Faso (UV) + Niger (NG) sur la fenêtre
[SNAPSHOT_DATE_FROM, SNAPSHOT_DATE_TO]. Sortie Parquet dans data/raw/.

Usage :
    python -m src.pipeline.extract
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from src.config import (
    BQ_TABLE_EVENTS,
    BQ_TABLE_MENTIONS,
    CAMEO_TARGETS,
    FIPS_TARGETS,
    METADATA_FILE,
    PROJECT_ROOT,
    RAW_DIR,
    SNAPSHOT_DATE_FROM,
    SNAPSHOT_DATE_TO,
)
from src.pipeline.bigquery_client import init_client, run_query_to_parquet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def build_events_query() -> str:
    """Construit la requête events filtrée 3 pays + 12 mois.

    Filtre sur _PARTITIONTIME EN PREMIER pour préserver le quota (impératif).
    """
    fips = ", ".join(f"'{c}'" for c in FIPS_TARGETS)
    cameo = ", ".join(f"'{c}'" for c in CAMEO_TARGETS)
    return f"""
        SELECT
          GLOBALEVENTID,
          SQLDATE, MonthYear, Year, FractionDate,
          Actor1Code, Actor1Name, Actor1CountryCode, Actor1Type1Code,
          Actor2Code, Actor2Name, Actor2CountryCode, Actor2Type1Code,
          IsRootEvent,
          EventCode, EventBaseCode, EventRootCode,
          QuadClass, GoldsteinScale,
          NumMentions, NumSources, NumArticles, AvgTone,
          Actor1Geo_Type, Actor1Geo_FullName, Actor1Geo_CountryCode,
          Actor1Geo_ADM1Code, Actor1Geo_Lat, Actor1Geo_Long,
          Actor2Geo_Type, Actor2Geo_FullName, Actor2Geo_CountryCode,
          Actor2Geo_ADM1Code, Actor2Geo_Lat, Actor2Geo_Long,
          ActionGeo_Type, ActionGeo_FullName, ActionGeo_CountryCode,
          ActionGeo_ADM1Code, ActionGeo_Lat, ActionGeo_Long,
          DATEADDED, SOURCEURL
        FROM `{BQ_TABLE_EVENTS}`
        WHERE _PARTITIONTIME >= TIMESTAMP("{SNAPSHOT_DATE_FROM.isoformat()}")
          AND _PARTITIONTIME <  TIMESTAMP("{SNAPSHOT_DATE_TO.isoformat()}")
          AND (
            ActionGeo_CountryCode IN ({fips})
            OR Actor1CountryCode  IN ({cameo})
            OR Actor2CountryCode  IN ({cameo})
          )
    """


def build_mentions_query() -> str:
    """Mentions associées aux events filtrés (jointure indirecte par GLOBALEVENTID).

    Note : on filtre les mentions sur la même fenêtre temporelle puis on
    laisse le clean.py joindre sur les events extraits — moins de données
    scannées qu'une jointure côté BigQuery.
    """
    return f"""
        SELECT
          GLOBALEVENTID,
          EventTimeDate, MentionTimeDate,
          MentionType, MentionSourceName, MentionIdentifier,
          SentenceID, Actor1CharOffset, Actor2CharOffset, ActionCharOffset,
          InRawText, Confidence,
          MentionDocLen, MentionDocTone, MentionDocTranslationInfo
        FROM `{BQ_TABLE_MENTIONS}`
        WHERE _PARTITIONTIME >= TIMESTAMP("{SNAPSHOT_DATE_FROM.isoformat()}")
          AND _PARTITIONTIME <  TIMESTAMP("{SNAPSHOT_DATE_TO.isoformat()}")
    """


def write_metadata(events_path: Path, mentions_path: Path) -> None:
    """Écrit data/_metadata.json avec date snapshot, hash, paths."""

    def _hash(p: Path) -> str:
        h = sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    meta = {
        "snapshot_extracted_at": datetime.utcnow().isoformat() + "Z",
        "snapshot_window": {
            "from": SNAPSHOT_DATE_FROM.isoformat(),
            "to": SNAPSHOT_DATE_TO.isoformat(),
        },
        "countries_fips": list(FIPS_TARGETS),
        "countries_cameo": list(CAMEO_TARGETS),
        "files": {
            "events": {
                "path": str(events_path.relative_to(PROJECT_ROOT)),
                "sha256_short": _hash(events_path),
            },
            "mentions": {
                "path": str(mentions_path.relative_to(PROJECT_ROOT)),
                "sha256_short": _hash(mentions_path),
            },
        },
    }
    METADATA_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    logger.info("Métadonnées écrites : %s", METADATA_FILE)


def main() -> None:
    logger.info(
        "Démarrage extraction snapshot %s -> %s",
        SNAPSHOT_DATE_FROM,
        SNAPSHOT_DATE_TO,
    )
    client = init_client()

    events_query = build_events_query()
    mentions_query = build_mentions_query()

    events_out = RAW_DIR / f"events_{SNAPSHOT_DATE_FROM}_{SNAPSHOT_DATE_TO}.parquet"
    mentions_out = (
        RAW_DIR / f"mentions_{SNAPSHOT_DATE_FROM}_{SNAPSHOT_DATE_TO}.parquet"
    )

    run_query_to_parquet(client, events_query, events_out)
    run_query_to_parquet(client, mentions_query, mentions_out)

    write_metadata(events_out, mentions_out)
    logger.info("Extraction terminée.")


if __name__ == "__main__":
    main()
