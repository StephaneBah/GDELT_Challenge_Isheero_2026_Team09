"""Client BigQuery — initialisation et exécution sécurisée.

Adapté de reicHerr/GDELT-Events-Analysis (MIT). Principales évolutions :
- Sortie Parquet (au lieu de CSV) pour les volumes analytiques.
- Garde-fou `maximum_bytes_billed` activé par défaut.
- Estimation dry-run avant exécution (évite de cramer le quota).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from src.config import BQ_LOCATION, BQ_MAX_BYTES_BILLED, GCP_PROJECT_ID
from src.pipeline.auth import setup_authentication

logger = logging.getLogger(__name__)


def init_client(
    project_id: Optional[str] = None,
    credentials_path: Optional[str] = None,
) -> bigquery.Client:
    """Initialise un client BigQuery.

    Deux modes d'authentification supportés (cf. src/pipeline/auth.py) :
    1. Service account (JSON) — si GOOGLE_APPLICATION_CREDENTIALS pointe
       sur un fichier valide.
    2. Application Default Credentials (ADC) — sinon, le client s'appuie
       sur les credentials gérés par `gcloud auth application-default login`.
    """
    project_id = project_id or GCP_PROJECT_ID
    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID manquant. Le renseigner dans .env ou en argument."
        )

    path = setup_authentication(credentials_path)
    client_params = {"project": project_id, "location": BQ_LOCATION}

    if path:
        # Mode service account explicite
        client_params["credentials"] = service_account.Credentials.from_service_account_file(path)
        mode = "service account"
    else:
        # Mode ADC : le SDK Google détecte automatiquement les credentials
        # depuis ~/.config/gcloud/application_default_credentials.json
        mode = "ADC (gcloud auth application-default)"

    client = bigquery.Client(**client_params)
    logger.info("Client BigQuery initialisé (projet=%s, mode=%s)", project_id, mode)
    return client


def estimate_query_cost(client: bigquery.Client, query: str) -> int:
    """Renvoie le nombre d'octets que la requête scannerait (dry-run).

    Permet d'éviter de lancer une requête trop coûteuse.
    """
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    job = client.query(query, job_config=job_config)
    bytes_processed = job.total_bytes_processed or 0
    logger.info(
        "Estimation dry-run : %.2f GB scannés",
        bytes_processed / 1024**3,
    )
    return bytes_processed


def run_query_to_parquet(
    client: bigquery.Client,
    query: str,
    output_path: Path,
    max_bytes_billed: int = BQ_MAX_BYTES_BILLED,
    confirm_above_gb: float = 5.0,
) -> Path:
    """Exécute une requête et écrit le résultat en Parquet.

    Args:
        client: client BigQuery initialisé.
        query: requête SQL à exécuter.
        output_path: chemin du fichier Parquet de sortie.
        max_bytes_billed: garde-fou — la requête échoue si elle dépasse.
        confirm_above_gb: au-delà, log un avertissement très visible.

    Returns:
        Le chemin du fichier Parquet créé.
    """
    estimated = estimate_query_cost(client, query)
    estimated_gb = estimated / 1024**3
    if estimated_gb > confirm_above_gb:
        logger.warning(
            "ATTENTION : la requête scannera environ %.2f GB. "
            "Quota BigQuery free tier = 1024 GB/mois.",
            estimated_gb,
        )

    job_config = bigquery.QueryJobConfig(maximum_bytes_billed=max_bytes_billed)
    job = client.query(query, job_config=job_config)
    df: pd.DataFrame = job.to_dataframe(progress_bar_type=None)

    logger.info(
        "Requête exécutée : %d lignes, %.2f GB facturés",
        len(df),
        (job.total_bytes_billed or 0) / 1024**3,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, engine="pyarrow", compression="snappy", index=False)
    logger.info("Parquet écrit : %s (%d lignes)", output_path, len(df))
    return output_path
