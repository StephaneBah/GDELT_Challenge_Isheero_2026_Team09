"""Extraction one-shot des événements GDELT sur 12 mois et 3 pays.

Snapshot figé : Bénin (BN) + Burkina Faso (UV) + Niger (NG) sur la fenêtre
[SNAPSHOT_DATE_FROM, SNAPSHOT_DATE_TO[. Sortie Parquet dans data/raw/.

Stratégie :
- Découpage **par mois** (12 sous-requêtes plus petites au lieu d'une seule)
  pour éviter le 'Response too large' lorsque la requête concentre 12 mois
  d'événements en une seule réponse BigQuery.
- Sélection limitée aux colonnes effectivement utilisées par les questions
  Q1/Q2/Q3 (réduit le volume de réponse).
- Mentions : non extraites par défaut (non utilisées par les questions).
  Activable via `--with-mentions` si besoin futur.

Usage :
    python -m src.pipeline.extract
    python -m src.pipeline.extract --with-mentions
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta
from hashlib import sha256
from pathlib import Path

import pandas as pd

from src.config import (
    BQ_TABLE_EVENTS,
    BQ_TABLE_MENTIONS,
    CAMEO_TARGETS_ALL,
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


# Colonnes events strictement utilisées par les questions Q1/Q2/Q3.
EVENT_COLUMNS = [
    "GLOBALEVENTID",
    "SQLDATE", "Year",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1Type1Code",
    "Actor2Code", "Actor2Name", "Actor2CountryCode", "Actor2Type1Code",
    "EventCode", "EventBaseCode", "EventRootCode",
    "QuadClass", "GoldsteinScale",
    "NumMentions", "NumSources", "NumArticles", "AvgTone",
    "ActionGeo_FullName", "ActionGeo_CountryCode", "ActionGeo_ADM1Code",
    "ActionGeo_Lat", "ActionGeo_Long",
    "SOURCEURL",
]


def _month_ranges(start: date, end: date) -> list[tuple[date, date]]:
    """Découpe [start, end[ en intervalles mensuels [from, to[."""
    ranges = []
    current = start
    while current < end:
        # Premier jour du mois suivant
        if current.month == 12:
            nxt = date(current.year + 1, 1, 1)
        else:
            nxt = date(current.year, current.month + 1, 1)
        ranges.append((current, min(nxt, end)))
        current = nxt
    return ranges


def build_events_query(date_from: date, date_to: date) -> str:
    """Requête events sur un intervalle [date_from, date_to[."""
    fips = ", ".join(f"'{c}'" for c in FIPS_TARGETS)
    cameo = ", ".join(f"'{c}'" for c in CAMEO_TARGETS_ALL)
    columns = ",\n          ".join(EVENT_COLUMNS)
    return f"""
        SELECT
          {columns}
        FROM `{BQ_TABLE_EVENTS}`
        WHERE _PARTITIONTIME >= TIMESTAMP("{date_from.isoformat()}")
          AND _PARTITIONTIME <  TIMESTAMP("{date_to.isoformat()}")
          AND (
            ActionGeo_CountryCode IN ({fips})
            OR Actor1CountryCode  IN ({cameo})
            OR Actor2CountryCode  IN ({cameo})
          )
    """


def build_mentions_query(date_from: date, date_to: date) -> str:
    """Mentions filtrées via JOIN avec les events ciblés (limite le volume)."""
    fips = ", ".join(f"'{c}'" for c in FIPS_TARGETS)
    cameo = ", ".join(f"'{c}'" for c in CAMEO_TARGETS_ALL)
    return f"""
        SELECT
          m.GLOBALEVENTID,
          m.EventTimeDate, m.MentionTimeDate,
          m.MentionType, m.MentionSourceName, m.MentionIdentifier,
          m.Confidence, m.MentionDocLen, m.MentionDocTone
        FROM `{BQ_TABLE_MENTIONS}` m
        JOIN (
          SELECT DISTINCT GLOBALEVENTID
          FROM `{BQ_TABLE_EVENTS}`
          WHERE _PARTITIONTIME >= TIMESTAMP("{date_from.isoformat()}")
            AND _PARTITIONTIME <  TIMESTAMP("{date_to.isoformat()}")
            AND (
              ActionGeo_CountryCode IN ({fips})
              OR Actor1CountryCode IN ({cameo})
              OR Actor2CountryCode IN ({cameo})
            )
        ) e USING (GLOBALEVENTID)
        WHERE m._PARTITIONTIME >= TIMESTAMP("{date_from.isoformat()}")
          AND m._PARTITIONTIME <  TIMESTAMP("{date_to.isoformat()}")
    """


def extract_events_in_chunks(client) -> Path:
    """Extrait les events mois par mois et les concatène en un seul Parquet."""
    months = _month_ranges(SNAPSHOT_DATE_FROM, SNAPSHOT_DATE_TO)
    logger.info("Extraction events en %d sous-requêtes mensuelles", len(months))

    chunks: list[pd.DataFrame] = []
    total_billed = 0
    for i, (d0, d1) in enumerate(months, start=1):
        logger.info("[%d/%d] Mois %s -> %s", i, len(months), d0, d1)
        query = build_events_query(d0, d1)
        # Exécution directe (sans passer par run_query_to_parquet pour
        # accumuler les chunks en mémoire avant un seul write)
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig()
        job = client.query(query, job_config=job_config)
        df = job.to_dataframe(progress_bar_type=None)
        billed = (job.total_bytes_billed or 0) / 1024**3
        total_billed += billed
        logger.info("  -> %d lignes, %.2f GB facturés", len(df), billed)
        chunks.append(df)

    df_all = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    out = RAW_DIR / f"events_{SNAPSHOT_DATE_FROM}_{SNAPSHOT_DATE_TO}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_parquet(out, engine="pyarrow", compression="snappy", index=False)
    logger.info(
        "Events totaux : %d lignes, %.2f GB facturés cumulés. Parquet : %s",
        len(df_all),
        total_billed,
        out,
    )
    return out


def extract_mentions_in_chunks(client) -> Path:
    """Extrait les mentions filtrées (JOIN avec events) mois par mois."""
    months = _month_ranges(SNAPSHOT_DATE_FROM, SNAPSHOT_DATE_TO)
    logger.info("Extraction mentions en %d sous-requêtes mensuelles", len(months))

    chunks: list[pd.DataFrame] = []
    total_billed = 0
    for i, (d0, d1) in enumerate(months, start=1):
        logger.info("[%d/%d] Mentions %s -> %s", i, len(months), d0, d1)
        query = build_mentions_query(d0, d1)
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig()
        job = client.query(query, job_config=job_config)
        df = job.to_dataframe(progress_bar_type=None)
        billed = (job.total_bytes_billed or 0) / 1024**3
        total_billed += billed
        logger.info("  -> %d lignes, %.2f GB facturés", len(df), billed)
        chunks.append(df)

    df_all = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    out = RAW_DIR / f"mentions_{SNAPSHOT_DATE_FROM}_{SNAPSHOT_DATE_TO}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_parquet(out, engine="pyarrow", compression="snappy", index=False)
    logger.info(
        "Mentions totales : %d lignes, %.2f GB facturés cumulés. Parquet : %s",
        len(df_all),
        total_billed,
        out,
    )
    return out


def write_metadata(events_path: Path, mentions_path: Path | None) -> None:
    """Écrit data/_metadata.json avec date snapshot, hash, paths."""

    def _hash(p: Path) -> str:
        h = sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()[:16]

    files = {
        "events": {
            "path": str(events_path.relative_to(PROJECT_ROOT)),
            "sha256_short": _hash(events_path),
        },
    }
    if mentions_path is not None:
        files["mentions"] = {
            "path": str(mentions_path.relative_to(PROJECT_ROOT)),
            "sha256_short": _hash(mentions_path),
        }

    meta = {
        "snapshot_extracted_at": datetime.utcnow().isoformat() + "Z",
        "snapshot_window": {
            "from": SNAPSHOT_DATE_FROM.isoformat(),
            "to": SNAPSHOT_DATE_TO.isoformat(),
        },
        "countries_fips": list(FIPS_TARGETS),
        "countries_cameo": list(CAMEO_TARGETS_ALL),
        "files": files,
    }
    METADATA_FILE.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    logger.info("Métadonnées écrites : %s", METADATA_FILE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--with-mentions",
        action="store_true",
        help="Extrait aussi la table mentions (non utilisée par Q1/Q2/Q3).",
    )
    args = parser.parse_args(argv)

    logger.info(
        "Démarrage extraction snapshot %s -> %s",
        SNAPSHOT_DATE_FROM,
        SNAPSHOT_DATE_TO,
    )
    client = init_client()

    events_out = extract_events_in_chunks(client)
    mentions_out = extract_mentions_in_chunks(client) if args.with_mentions else None

    write_metadata(events_out, mentions_out)
    logger.info("Extraction terminée.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
