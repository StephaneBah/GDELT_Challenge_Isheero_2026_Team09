"""Constantes partagées par tous les modules.

Tout ce qui est paramétrable globalement vit ici : chemins, fenêtre temporelle,
codes pays, mapping CAMEO -> domaines de risque, etc.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Charge .env si présent (silencieux sinon)
load_dotenv()

# --- Racine du projet ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# --- Chemins data ---
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
MODELS_DIR = DATA_DIR / "models"
METADATA_FILE = DATA_DIR / "_metadata.json"

# --- Fenêtre temporelle du snapshot ---
# Année calendaire 2025 complète, conformément à la consigne du hackathon.
# Intervalle semi-ouvert [FROM, TO) : SNAPSHOT_DATE_TO est exclusive.
SNAPSHOT_DATE_FROM = date.fromisoformat(os.getenv("SNAPSHOT_DATE_FROM", "2025-01-01"))
SNAPSHOT_DATE_TO = date.fromisoformat(os.getenv("SNAPSHOT_DATE_TO", "2026-01-01"))

# --- Pays cibles ---
# Codes FIPS 10-4 (ActionGeo_CountryCode dans GDELT).
# ATTENTION : le brief du hackathon indiquait "BC" pour le Bénin — c'est une
# erreur typographique. BC est le code FIPS du **Botswana**.
# Bénin = BN, Burkina Faso = UV (ex-Upper Volta), Niger = NG.
FIPS_BENIN = "BN"
FIPS_BURKINA = "UV"
FIPS_NIGER = "NG"
FIPS_TARGETS = (FIPS_BENIN, FIPS_BURKINA, FIPS_NIGER)

# Mapping FIPS ADM1Code -> nom officiel du département béninois.
# Construit empiriquement à partir des données GDELT 2025 (cf. notebook).
# La forme du code est BN<NN> où NN est numéroté approximativement par
# ordre alphabétique des départements officiels.
FIPS_ADM1_TO_DEPT: dict[str, str] = {
    "BN07": "Alibori",
    "BN08": "Atacora",
    "BN09": "Atlantique",
    "BN10": "Borgou",
    "BN11": "Collines",
    "BN12": "Couffo",
    "BN13": "Donga",
    "BN14": "Littoral",
    "BN15": "Mono",
    "BN16": "Ouémé",
    "BN17": "Plateau",
    "BN18": "Zou",
    # BN et BN00 : country-level / général, non attribuable à un département.
}

# Codes CAMEO acteurs (Actor1CountryCode / Actor2CountryCode)
#
# La taxonomie CAMEO n'est PAS strictement ISO-3 et a évolué selon les
# versions du codebook. Pour éviter une extraction silencieusement
# incomplète, on liste pour chaque pays cible TOUTES les variantes
# plausibles ; la clause IN du SQL utilise `CAMEO_TARGETS_ALL` qui
# concatène toutes les variantes.
#
# Le script `src/pipeline/discover_codes.py` interroge BigQuery sur un
# échantillon de 7 jours et liste les codes réellement présents — à
# lancer une fois avant la grande extraction (`make discover-codes`).
CAMEO_BENIN = "BEN"
CAMEO_BURKINA = "BFA"  # ISO-3 ; certaines versions du codebook utilisent "BFO"
CAMEO_NIGER = "NER"    # ISO-3 ; ne PAS confondre avec "NGR" qui désigne le Nigeria
CAMEO_TARGETS = (CAMEO_BENIN, CAMEO_BURKINA, CAMEO_NIGER)

# Variantes CAMEO connues, par pays. Utilisées en SQL pour capturer
# tous les events indépendamment de l'évolution du codebook GDELT.
CAMEO_VARIANTS: dict[str, tuple[str, ...]] = {
    CAMEO_BENIN:   ("BEN",),
    CAMEO_BURKINA: ("BFA", "BFO"),
    CAMEO_NIGER:   ("NER",),  # NGR exclu : ambigu avec Nigeria
}

# Liste plate de toutes les variantes — utilisable directement dans IN(...).
CAMEO_TARGETS_ALL: tuple[str, ...] = tuple(
    code for variants in CAMEO_VARIANTS.values() for code in variants
)

# --- Départements béninois (admin1) ---
# 12 départements officiels — utilisés pour la maille de référence
BENIN_DEPARTMENTS = (
    "Alibori",
    "Atacora",
    "Atlantique",
    "Borgou",
    "Collines",
    "Couffo",
    "Donga",
    "Littoral",
    "Mono",
    "Ouémé",
    "Plateau",
    "Zou",
)

# --- Doctrine : domaines de risque ---
# Mapping CAMEO root code -> domaine de risque lisible.
# 5-7 catégories pour rendre l'interface compréhensible par un non-codeur.
# Cf. docs/03_cameo_domains_mapping.md pour la justification détaillée.
CAMEO_TO_DOMAIN = {
    # Politique (déclarations, consultations, désaccords)
    "01": "politique",
    "02": "politique",
    "03": "politique",
    "04": "politique",
    "05": "politique",
    "08": "politique",
    "09": "politique",
    "10": "politique",
    "11": "politique",
    "12": "politique",
    "13": "politique",
    "14": "politique",
    "16": "politique",
    # Coopération matérielle => économique (sera affiné par sub-codes)
    "06": "economique",
    # Aide humanitaire / sanitaire
    "07": "humanitaire",
    # Posture militaire, coercition, assauts, combats, violences de masse
    "15": "securitaire",
    "17": "securitaire",
    "18": "securitaire",
    "19": "securitaire",
    "20": "securitaire",
}

DOMAINS = ("securitaire", "politique", "economique", "humanitaire", "informationnel")

# --- Labels lisibles pour affichage (dashboard, insights, pitch) ---

DOMAIN_LABELS: dict[str, str] = {
    "securitaire":    "Sécuritaire",
    "politique":      "Politique",
    "economique":     "Économique",
    "humanitaire":    "Humanitaire",
    "informationnel": "Informationnel",
}

# Codes acteurs CAMEO → labels compréhensibles par un non-spécialiste.
# Inclut : codes pays ISO-3, types génériques, combinés pays+type.
ACTOR_LABELS: dict[str, str] = {
    # Pays de la zone
    "BEN": "Bénin",
    "NER": "Niger",
    "NGA": "Nigeria",
    "BFA": "Burkina Faso",
    "MLI": "Mali",
    "GHA": "Ghana",
    "TGO": "Togo",
    "CIV": "Côte d'Ivoire",
    "SEN": "Sénégal",
    "GMB": "Gambie",
    "GNB": "Guinée-Bissau",
    "CMR": "Cameroun",
    # Grands acteurs mondiaux
    "USA": "États-Unis",
    "FRA": "France",
    "CHN": "Chine",
    "RUS": "Russie",
    "GBR": "Royaume-Uni",
    "DEU": "Allemagne",
    # Codes régionaux génériques
    "AFR": "Acteurs africains",
    "WEU": "Europe occidentale",
    "UNO": "Nations Unies",
    "ECW": "CEDEAO",
    # Types d'acteurs génériques
    "GOV": "Gouvernements",
    "MIL": "Forces armées",
    "NGO": "ONG",
    "IGO": "Organisations internationales",
    "CVL": "Société civile",
    "MED": "Médias",
    "UAF": "Forces armées non-identifiées",
    "REB": "Groupes armés non-étatiques",
    "SPY": "Services de renseignement",
    # Acteurs combinés pays + type
    "BENGOV":  "Gouvernement béninois",
    "BENMIL":  "Armée béninoise",
    "NERGOV":  "Gouvernement du Niger",
    "NERMIL":  "Armée du Niger",
    "NGAGOV":  "Gouvernement nigérian",
    "NGAMIL":  "Armée nigériane",
    "BFAGOV":  "Gouvernement burkinabè",
    "BFAMIL":  "Armée burkinabè",
    "USAGOV":  "Gouvernement américain",
    "FRAGOV":  "Gouvernement français",
    "ECWIGO":  "CEDEAO",
    "UNGOV":   "Nations Unies",
    "UNOCHA":  "OCHA (aide humanitaire ONU)",
}

_ACTOR_TYPE_SUFFIXES: dict[str, str] = {
    "GOV": "Gouvernement",
    "MIL": "Armée",
    "NGO": "ONG",
    "IGO": "Org. internationale",
    "CVL": "Civils",
    "MED": "Médias",
    "UAF": "Forces armées",
    "REB": "Groupe armé",
}


def humanize_actor(code: str) -> str:
    """Convertit un code acteur CAMEO en label lisible.

    Stratégie :
    1. Lookup direct dans ACTOR_LABELS.
    2. Parsing structurel : 3 chars pays + suffix type.
    3. Retourne le code brut en dernier recours.
    """
    if not code or not isinstance(code, str):
        return "Inconnu"
    if code in ACTOR_LABELS:
        return ACTOR_LABELS[code]
    country_label = ACTOR_LABELS.get(code[:3], code[:3])
    suffix = code[3:] if len(code) > 3 else ""
    type_label = _ACTOR_TYPE_SUFFIXES.get(suffix, suffix)
    if type_label:
        return f"{type_label} ({country_label})"
    return country_label


# --- BigQuery ---
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
BQ_LOCATION = os.getenv("BIGQUERY_LOCATION", "US")

# Tables GDELT v2
BQ_TABLE_EVENTS = "gdelt-bq.gdeltv2.events_partitioned"
BQ_TABLE_MENTIONS = "gdelt-bq.gdeltv2.eventmentions_partitioned"
BQ_TABLE_GKG = "gdelt-bq.gdeltv2.gkg_partitioned"

# Garde-fou de quota — refuse une requête qui scannerait plus de 50 GB
BQ_MAX_BYTES_BILLED = 50 * 1024**3
