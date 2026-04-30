"""Contrats partagés par toutes les questions de recherche.

Ces trois objets — `Filters`, `Result`, `Question` — sont les seuls que la
couche dashboard et le runner CLI ont besoin de connaître. Toute question
concrète (Q1, Q2, …) DOIT respecter ces contrats.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal, Protocol, runtime_checkable

import pandas as pd
import plotly.graph_objects as go


ConfidenceTier = Literal["strict", "large", "all"]


@dataclass(frozen=True)
class Filters:
    """Filtres globaux applicables à toute question.

    Volontairement frozen pour éviter les mutations accidentelles dans les
    orchestrateurs. Construire un nouveau Filters avec `dataclasses.replace`
    si on veut altérer un champ.
    """

    date_from: date | None = None
    date_to: date | None = None
    countries: tuple[str, ...] = ()  # codes FIPS
    risk_domains: tuple[str, ...] = ()  # cf. config.DOMAINS
    confidence: ConfidenceTier = "all"
    departments: tuple[str, ...] = ()  # noms normalisés (Bénin uniquement)

    def describe(self) -> str:
        """Une-ligne résumant les filtres pour les logs / titres de figure."""
        parts = []
        if self.date_from or self.date_to:
            parts.append(f"{self.date_from or '…'} → {self.date_to or '…'}")
        if self.countries:
            parts.append("pays=" + ",".join(self.countries))
        if self.risk_domains:
            parts.append("dom=" + ",".join(self.risk_domains))
        if self.confidence != "all":
            parts.append(f"conf={self.confidence}")
        if self.departments:
            parts.append("dépt=" + ",".join(self.departments))
        return " · ".join(parts) or "(aucun filtre)"


@dataclass
class Result:
    """Sortie standard d'une question.

    - `metrics` : valeurs scalaires affichables en KPI.
    - `tables` : DataFrames intermédiaires utiles (export CSV, exploration).
    - `figures` : figures Plotly prêtes à être insérées dans un dashboard.
    - `insight_text` : phrase narrative à inclure dans le pitch.
    - `metadata` : timing, filtres appliqués, hash de données, etc.
    """

    question_id: str
    title: str
    metrics: dict[str, Any] = field(default_factory=dict)
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    figures: dict[str, go.Figure] = field(default_factory=dict)
    insight_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Question(Protocol):
    """Protocole minimal qu'une question doit respecter.

    Convention : chaque module `src/questions/q*.py` expose une variable
    `QUESTION` qui est une instance respectant ce protocole.
    """

    id: str
    title: str

    def run(self, filters: Filters) -> Result: ...
