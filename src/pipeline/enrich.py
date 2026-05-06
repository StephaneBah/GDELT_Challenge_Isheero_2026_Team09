"""Enrichissement : data/interim/ -> data/processed/.

Ajoute aux events :
- `risk_domain` : domaine de risque lisible (cf. doctrine, principe 3)
- `confidence_tier` : strict / large (cf. doctrine, principe 2)
- (optionnel) `dept_normalized` : nom de département béninois normalisé

Usage :
    python -m src.pipeline.enrich
"""
from __future__ import annotations

import logging

import pandas as pd

from src.config import (
    BENIN_DEPARTMENTS,
    CAMEO_TO_DOMAIN,
    FIPS_ADM1_TO_DEPT,
    FIPS_BENIN,
    INTERIM_DIR,
    PROCESSED_DIR,
)

# Sanity check : DEPT_ALIASES doit couvrir tous les départements officiels.
# (Vérification en haut du module pour échouer tôt si config.py change.)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def add_risk_domain(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la colonne `risk_domain` à partir du root code CAMEO."""
    df["risk_domain"] = (
        df["EventRootCode"].astype(str).str.zfill(2).map(CAMEO_TO_DOMAIN)
    )
    df["risk_domain"] = df["risk_domain"].fillna("autre")
    return df


def add_confidence_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Tier strict : >=3 sources et géoloc renseignée. Tier large : tout le reste."""
    strict_mask = (
        (df["NumSources"].fillna(0) >= 3)
        & (df["ActionGeo_Lat"].notna())
        & (df["ActionGeo_Long"].notna())
    )
    df["confidence_tier"] = strict_mask.map({True: "strict", False: "large"})
    return df


# Aliases connus pour les variantes orthographiques GDELT/GeoNames.
# Toute valeur dans le nom complet GDELT est lowercase-matched contre
# l'une des variantes de chaque liste pour résoudre vers le nom officiel.
DEPT_ALIASES: dict[str, list[str]] = {
    "Alibori": ["alibori"],
    "Atacora": ["atacora", "atakora"],            # GeoNames utilise souvent "Atakora"
    "Atlantique": ["atlantique", "atlanique"],    # variante orthographique observée
    "Borgou": ["borgou"],
    "Collines": ["collines"],
    "Couffo": ["couffo", "kouffo"],               # variante archaïque "Kouffo"
    "Donga": ["donga"],
    "Littoral": ["littoral"],
    "Mono": ["mono"],
    "Ouémé": ["ouémé", "oueme"],                  # accents souvent perdus dans GDELT
    "Plateau": ["plateau"],
    "Zou": ["zou"],
}

assert set(DEPT_ALIASES.keys()) == set(BENIN_DEPARTMENTS), (
    "DEPT_ALIASES doit lister exactement les départements officiels "
    "(BENIN_DEPARTMENTS dans src/config.py). Synchroniser les deux."
)


def normalize_benin_admin1(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise le nom de département pour les events béninois.

    Stratégie en deux passes :
    1. **Mapping ADM1Code** (canonique, fiable) : utilise FIPS_ADM1_TO_DEPT
       pour résoudre les codes BN07..BN18 vers les 12 départements.
    2. **Fallback texte** : pour les events sans ADM1Code mais avec un
       département mentionné dans `ActionGeo_FullName`, table d'aliases
       pour les variantes orthographiques (Atakora->Atacora, Oueme->Ouémé,
       Kouffo->Couffo, Atlanique->Atlantique).

    Les events tagués au niveau pays (ADM1Code='BN' ou vide) restent en
    `dept_normalized=NA` — c'est volontaire, ils ne sont pas localisables.
    """
    df["dept_normalized"] = pd.NA
    benin_mask = df["ActionGeo_CountryCode"] == FIPS_BENIN

    # Passe 1 : mapping ADM1Code (canonique)
    adm1_match = df.loc[benin_mask, "ActionGeo_ADM1Code"].map(FIPS_ADM1_TO_DEPT)
    df.loc[benin_mask, "dept_normalized"] = adm1_match

    # Passe 2 : fallback texte sur les events encore non résolus
    unmatched = benin_mask & df["dept_normalized"].isna()
    full = df.loc[unmatched, "ActionGeo_FullName"].fillna("").str.lower()
    for dept, aliases in DEPT_ALIASES.items():
        for alias in aliases:
            m = full.str.contains(alias, regex=False, na=False)
            df.loc[unmatched & m.reindex(df.index, fill_value=False), "dept_normalized"] = dept

    return df


def main() -> None:
    events = pd.read_parquet(INTERIM_DIR / "events.parquet")
    events = add_risk_domain(events)
    events = add_confidence_tier(events)
    events = normalize_benin_admin1(events)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "events_enriched.parquet"
    events.to_parquet(out, compression="snappy", index=False)
    logger.info(
        "Enrichi écrit : %s (%d lignes, %d en strict)",
        out,
        len(events),
        (events["confidence_tier"] == "strict").sum(),
    )


if __name__ == "__main__":
    main()
