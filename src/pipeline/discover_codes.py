"""Diagnostic — audit des codes pays CAMEO sur échantillon BigQuery.

À lancer UNE FOIS avant la grande extraction (`make extract`) pour valider
que les codes configurés dans `src/config.py` correspondent aux valeurs
réellement présentes dans GDELT.

La taxonomie CAMEO acteurs n'est PAS strictement ISO-3 et a évolué selon
les versions du codebook. Sans ce check, une mauvaise valeur entraîne une
extraction silencieusement incomplète : les events où le Bénin agit avec
le Niger (ou réciproquement) seraient ratés, sans aucun message d'erreur.

Stratégie :
1. Liste tous les codes acteurs apparaissant dans les events qui ont une
   action géographique au Bénin / Burkina / Niger sur 7 jours récents.
2. Affiche le top 30 par fréquence.
3. Pour chaque pays cible, vérifie si AU MOINS UNE de ses variantes
   (CAMEO_VARIANTS) apparaît effectivement.
4. Suggère la mise à jour de config.py si une variante manque ou si une
   variante non listée domine.

Coût BigQuery : ~1-2 GB scannés (1% du quota mensuel free tier).

Usage :
    python -m src.pipeline.discover_codes
    python -m src.pipeline.discover_codes --days 30
    make discover-codes
"""
from __future__ import annotations

import argparse
import logging
from typing import Iterable

import pandas as pd

from src.config import (
    BQ_TABLE_EVENTS,
    CAMEO_VARIANTS,
    FIPS_TARGETS,
)
from src.pipeline.bigquery_client import init_client

logger = logging.getLogger(__name__)


def build_audit_query(days: int = 7) -> str:
    """Requête d'audit : top codes acteurs autour des events BN/UV/NG."""
    fips = ", ".join(f"'{c}'" for c in FIPS_TARGETS)
    return f"""
        SELECT
          Actor1CountryCode AS code,
          COUNT(*) AS n_events,
          COUNT(DISTINCT Actor1Name) AS n_distinct_actors,
          STRING_AGG(DISTINCT Actor1Name LIMIT 3) AS sample_actors
        FROM `{BQ_TABLE_EVENTS}`
        WHERE _PARTITIONTIME >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
          AND ActionGeo_CountryCode IN ({fips})
          AND Actor1CountryCode IS NOT NULL
        GROUP BY Actor1CountryCode
        ORDER BY n_events DESC
        LIMIT 30
    """


def audit(days: int = 7) -> pd.DataFrame:
    """Lance la requête et renvoie le DataFrame résultat."""
    client = init_client()
    query = build_audit_query(days)
    logger.info("Audit sur %d jours autour de %s", days, ", ".join(FIPS_TARGETS))
    job = client.query(query)
    df = job.to_dataframe(progress_bar_type=None)
    logger.info(
        "Audit terminé : %d codes distincts trouvés, %.2f GB facturés",
        len(df),
        (job.total_bytes_billed or 0) / 1024**3,
    )
    return df


def diagnose(df: pd.DataFrame) -> None:
    """Compare les codes trouvés à la configuration et alerte si dérive."""
    found_codes = set(df["code"].dropna().astype(str))

    print()
    print("=" * 70)
    print("DIAGNOSTIC DES CODES CAMEO ACTEURS")
    print("=" * 70)

    # Top 30
    print()
    print("Top codes acteurs présents dans les events autour de BN/UV/NG :")
    print()
    print(df.to_string(index=False, max_colwidth=40))

    # Audit par pays cible
    print()
    print("-" * 70)
    print("Audit par pays cible (CAMEO_VARIANTS dans config.py) :")
    print()
    issues: list[str] = []
    for primary, variants in CAMEO_VARIANTS.items():
        matched: list[tuple[str, int]] = []
        for v in variants:
            if v in found_codes:
                row = df[df["code"] == v].iloc[0]
                matched.append((v, int(row["n_events"])))

        if matched:
            best = max(matched, key=lambda t: t[1])
            note = f"OK — variante {best[0]!r} dominante ({best[1]} events sur 7j)"
            if best[0] != primary:
                note += f"  ⚠️  primary={primary!r} dans config — envisager de basculer"
            print(f"  {primary:>8}  variantes testées={variants}  {note}")
        else:
            print(f"  {primary:>8}  variantes testées={variants}  ❌ AUCUNE TROUVÉE")
            issues.append(
                f"Aucune variante de {primary} ({variants}) dans les données. "
                f"Inspecter le top 30 ci-dessus pour trouver le bon code."
            )

    # Détection de codes plausibles non listés (ex: si NGR apparaît en force)
    suspicious_unknown = df[
        ~df["code"].isin(set(c for vs in CAMEO_VARIANTS.values() for c in vs))
        & (df["n_events"] > 50)
    ]
    if not suspicious_unknown.empty:
        print()
        print("-" * 70)
        print("Codes non listés dans config qui apparaissent fortement (>50 events) :")
        print()
        print(suspicious_unknown.to_string(index=False, max_colwidth=40))
        print()
        print("Pour info, à examiner. Pas forcément à ajouter.")

    print()
    print("=" * 70)
    if issues:
        print(f"  ⚠️  {len(issues)} problème(s) détecté(s) :")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print("  → Mettre à jour CAMEO_VARIANTS dans src/config.py si besoin.")
    else:
        print("  ✅ Tous les pays cibles ont au moins une variante présente.")
    print("=" * 70)
    print()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Fenêtre d'audit en jours (défaut : 7).",
    )
    args = parser.parse_args(list(argv) if argv else None)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    try:
        df = audit(days=args.days)
    except Exception as e:  # noqa: BLE001
        logger.error("Échec de la requête d'audit : %s", e)
        return 1

    if df.empty:
        logger.error("Aucun résultat. Vérifier credentials et fenêtre temporelle.")
        return 1

    diagnose(df)
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
