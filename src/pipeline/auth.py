"""Authentification Google Cloud.

Adapté de reicHerr/GDELT-Events-Analysis (MIT) — `setup_authentication.py`.
Modifications : intégration au layout `src/`, utilisation de python-dotenv,
suppression du logger basicConfig en module-level.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def setup_authentication(
    credentials_path: Optional[str] = None,
    env_var: str = "GOOGLE_APPLICATION_CREDENTIALS",
) -> str:
    """Configure l'authentification Google Cloud via variable d'environnement.

    Args:
        credentials_path: chemin vers le fichier JSON du service account.
            Si None, utilise la valeur déjà présente dans l'environnement.
        env_var: nom de la variable d'environnement à positionner.

    Returns:
        Le chemin effectivement utilisé.

    Raises:
        FileNotFoundError: si le chemin fourni n'existe pas.
        PermissionError: si le fichier n'est pas lisible.
    """
    path = credentials_path or os.getenv(env_var)
    if not path:
        raise ValueError(
            f"Aucun chemin de credentials fourni et {env_var} non définie. "
            "Définir GOOGLE_APPLICATION_CREDENTIALS dans .env."
        )

    if not os.path.isfile(path):
        raise FileNotFoundError(f"Fichier de credentials introuvable : {path}")

    if not os.access(path, os.R_OK):
        raise PermissionError(f"Fichier de credentials non lisible : {path}")

    os.environ[env_var] = path
    logger.info("Authentification GCP configurée via %s", path)
    return path
