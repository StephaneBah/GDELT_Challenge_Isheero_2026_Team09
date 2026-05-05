"""Authentification Google Cloud — deux modes supportés.

1. **Service account (JSON)** — plus robuste, recommandé en production.
   Variable `GOOGLE_APPLICATION_CREDENTIALS` pointant sur un fichier JSON.

2. **Application Default Credentials (ADC)** — login navigateur, plus rapide
   pour le développement. Activé via `gcloud auth application-default login`.
   Aucun fichier requis ; les credentials sont stockés dans
   `~/.config/gcloud/application_default_credentials.json`.

Si `GOOGLE_APPLICATION_CREDENTIALS` est définie et pointe sur un fichier
existant, on l'utilise. Sinon on bascule sur ADC. Le client BigQuery
gère les deux cas automatiquement.

Adapté initialement de reicHerr/GDELT-Events-Analysis (MIT).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def setup_authentication(
    credentials_path: Optional[str] = None,
    env_var: str = "GOOGLE_APPLICATION_CREDENTIALS",
) -> Optional[str]:
    """Configure l'authentification Google Cloud.

    Args:
        credentials_path: chemin explicite vers un JSON service account.
            Si None, lit la variable d'environnement `env_var`.
            Si elle est vide ou pointe sur un fichier inexistant, on bascule
            silencieusement sur Application Default Credentials (ADC).
        env_var: nom de la variable d'environnement (défaut : standard Google).

    Returns:
        Le chemin du fichier JSON si l'authentification par service account
        est utilisée, ou None si on s'appuie sur ADC.
    """
    path = credentials_path or os.getenv(env_var)

    # Mode 1 : service account explicite
    if path and os.path.isfile(path):
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Fichier de credentials non lisible : {path}")
        os.environ[env_var] = path
        logger.info("Authentification GCP : service account via %s", path)
        return path

    # Mode 2 : Application Default Credentials (gcloud auth application-default login)
    logger.info(
        "Authentification GCP : Application Default Credentials (ADC). "
        "Si non configuré, lancer : gcloud auth application-default login"
    )
    return None
