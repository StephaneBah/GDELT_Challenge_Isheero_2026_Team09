"""Runner CLI pour exécuter une question de recherche.

Usage :
    python -m src.questions.runner --list
    python -m src.questions.runner --question Q1
    python -m src.questions.runner --question Q1 --confidence strict --countries BC,UV

Le runner ne contient AUCUNE logique d'analyse. Il :
1. Lit `questions.yaml` (manifest) pour la liste et les métadonnées.
2. Importe dynamiquement `src.questions.<id>` qui doit exposer `QUESTION`.
3. Construit un `Filters` à partir des arguments CLI.
4. Appelle `QUESTION.run(filters)` et journalise le `Result`.
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
from datetime import date
from pathlib import Path

import yaml

from src.config import PROJECT_ROOT
from src.questions.base import Filters, Result

logger = logging.getLogger(__name__)
MANIFEST_PATH = PROJECT_ROOT / "questions.yaml"


def load_manifest() -> dict:
    """Charge le manifest YAML. Vide si fichier absent."""
    if not MANIFEST_PATH.exists():
        return {"version": 1, "questions": []}
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {"version": 1, "questions": []}


def list_questions() -> None:
    """Affiche les questions du manifest."""
    manifest = load_manifest()
    questions = manifest.get("questions", [])
    if not questions:
        print("Manifest vide. Ajouter des entrées dans questions.yaml.")
        return
    print(f"{'ID':<6} {'Titre':<40} {'Owner':<15} {'Status':<12}")
    print("-" * 75)
    for q in questions:
        print(
            f"{q.get('id', '?'):<6} "
            f"{q.get('title', '?'):<40} "
            f"{q.get('owner', '?'):<15} "
            f"{q.get('status', '?'):<12}"
        )


def _resolve_module_name(question_id: str) -> str:
    """Cherche le nom du module dans le manifest. Fallback : src.questions.<id>."""
    manifest = load_manifest()
    for q in manifest.get("questions", []):
        if q.get("id", "").lower() == question_id.lower() and q.get("module"):
            return q["module"]
    return f"src.questions.{question_id.lower()}"


def run_question(question_id: str, filters: Filters) -> Result:
    """Importe le module et exécute la question."""
    module_name = _resolve_module_name(question_id)
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"Module {module_name} introuvable. Vérifier le champ `module` "
            f"dans questions.yaml ou créer le fichier correspondant."
        ) from e

    if not hasattr(module, "QUESTION"):
        raise AttributeError(
            f"{module_name} doit exposer une variable `QUESTION` "
            "(instance respectant le protocole `Question`)."
        )

    logger.info("Lancement %s · filtres : %s", question_id, filters.describe())
    result = module.QUESTION.run(filters)
    logger.info(
        "%s terminée : %d métriques · %d tables · %d figures",
        question_id,
        len(result.metrics),
        len(result.tables),
        len(result.figures),
    )
    return result


def parse_filters(args: argparse.Namespace) -> Filters:
    """Convertit les arguments CLI en `Filters`."""
    return Filters(
        date_from=date.fromisoformat(args.date_from) if args.date_from else None,
        date_to=date.fromisoformat(args.date_to) if args.date_to else None,
        countries=tuple(args.countries.split(",")) if args.countries else (),
        risk_domains=tuple(args.domains.split(",")) if args.domains else (),
        confidence=args.confidence,
        departments=tuple(args.departments.split(",")) if args.departments else (),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Runner Bénin Risk Map — exécute une question de recherche."
    )
    parser.add_argument("--list", action="store_true", help="Liste les questions du manifest")
    parser.add_argument("--question", help="ID de la question à exécuter (ex: Q1)")
    parser.add_argument("--date-from", dest="date_from", help="Date début (YYYY-MM-DD)")
    parser.add_argument("--date-to", dest="date_to", help="Date fin (YYYY-MM-DD)")
    parser.add_argument("--countries", help="Codes FIPS séparés par virgule (ex: BC,UV)")
    parser.add_argument("--domains", help="Domaines de risque séparés par virgule")
    parser.add_argument(
        "--confidence",
        choices=["strict", "large", "all"],
        default="all",
        help="Tier de confiance",
    )
    parser.add_argument("--departments", help="Départements béninois séparés par virgule")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.list:
        list_questions()
        return 0

    if not args.question:
        parser.error("--question requis (ou --list pour voir les questions)")

    filters = parse_filters(args)
    run_question(args.question, filters)
    return 0


if __name__ == "__main__":
    sys.exit(main())
