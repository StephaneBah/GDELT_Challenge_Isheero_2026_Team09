# Architecture modulaire

> Quatre couches, dépendances en cascade. Un orchestrateur de question
> compose les couches du dessous, jamais l'inverse.

---

## Schéma général

```
┌──────────────────────────────────────────────────────────┐
│  src/pipeline/      Extraction → enrichissement → stories │   (préparation)
│                     [bigquery, clean, enrich, stories]    │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  src/analytics/     Primitives pures (DataFrame → DF)     │
│                     [aggregate, change_points, network_ops] │
│                                                          │
│  src/ml/            Modèles entraînés (HF, sklearn)       │
│                     [sentiment]                          │
│                                                          │
│  src/viz/           Factories de figures Plotly           │
│                     [maps, timeseries, network]          │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  src/questions/     Orchestrateurs (1 fichier par Q)      │
│                     [base, runner, q1, q2, q3, ...]      │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  Consommateurs : dashboard/, notebooks/, reports/        │
└──────────────────────────────────────────────────────────┘
```

Le manifest YAML (`questions.yaml`, à la racine) **documente** chaque
question pour le README, le dashboard et le runner CLI. Il **n'exécute
pas** : l'exécution reste du Python explicite dans les modules de
`src/questions/`.

---

## Règles d'or

1. **Dépendances unidirectionnelles**.
   - `analytics/`, `ml/`, `viz/` ne dépendent **jamais** de `questions/`.
   - `questions/` peut importer `analytics/`, `ml/`, `viz/`, `pipeline/`.
   - `pipeline/` ne dépend de **rien** dans le reste de `src/` (sauf `config`).
2. **Pas de moteur générique**. Pas de `executor.run_pipeline_from_yaml(...)`.
   Chaque question est un orchestrateur Python explicite. Lisible, débogable,
   sans magie.
3. **Pas d'I/O dans `analytics/`, `ml/`, `viz/`**. Ces couches reçoivent
   des DataFrames et renvoient des DataFrames ou des figures. Le chargement
   de `data/processed/*.parquet` se fait dans la couche `questions/` ou
   le dashboard.
4. **Filters frozen, Result mutable**. `Filters` est une dataclass immuable
   (passée partout sans risque). `Result` est mutable (l'orchestrateur le
   construit progressivement).
5. **Une question = un fichier**. `src/questions/q1_terrain.py`,
   `q2_tone.py`, etc. Chaque module expose une variable `QUESTION` qui
   respecte le protocole `Question` de `base.py`.

---

## Conventions de la couche `analytics/`

- Fonctions **pures** (pas d'effet de bord, pas d'I/O).
- Signatures explicites : `aggregate_by_admin1(df, value_col, *, country_col=...)`
- Arguments nommés (`*,`) pour tout ce qui n'est pas obligatoire.
- Type hints partout.
- Préférer renvoyer un nouveau DataFrame plutôt que muter l'entrée.

## Conventions de la couche `ml/`

- Lazy-load des modèles (téléchargement HF) pour ne pas pénaliser les imports.
- Une fonction d'entrée publique par modèle (ex. `score_titles(titles)`).
- Pas de viz, pas d'agrégation.

## Conventions de la couche `viz/`

- Une factory = une fonction qui prend des données prêtes et renvoie une
  `plotly.graph_objects.Figure`.
- Pas de `df.groupby(...)` dans `viz/` — c'est le rôle d'`analytics/`.
- Pas de `df.read_parquet(...)` — c'est le rôle de la couche du dessus.
- Tous les paramètres de mise en forme (titre, couleur) en arguments avec
  défauts sensibles.

## Conventions de la couche `questions/`

Chaque module `src/questions/q*.py` :

```python
from dataclasses import dataclass

import pandas as pd

from src.config import PROCESSED_DIR
from src.questions.base import Filters, Question, Result
from src.analytics import aggregate
from src.viz import maps


@dataclass
class _Q1:
    id: str = "Q1"
    title: str = "Le terrain"

    def run(self, filters: Filters) -> Result:
        # 1. Charger les données
        events = pd.read_parquet(PROCESSED_DIR / "events_enriched.parquet")
        # 2. Appliquer filters
        # 3. Composer analytics + ml + viz
        # 4. Construire et retourner un Result
        ...


QUESTION = _Q1()
```

Et dans `questions.yaml`, on déclare les métadonnées correspondantes
(titre public, owner, primitives utilisées, outputs attendus, etc.).

---

## Pourquoi cette architecture (et pas plus simple, et pas plus complexe)

**Pourquoi pas plus simple** (« mettre tout dans des notebooks ») :
- Pas de réutilisabilité entre Q1, Q2, Q3.
- Pas de tests possibles sur les primitives.
- Le dashboard ne peut pas réinvoquer un calcul sans dupliquer.
- Le critère « reproductibilité » du hackathon passe mal.

**Pourquoi pas plus complexe** (« moteur générique piloté par YAML ») :
- Coût d'investissement disproportionné en 5 jours.
- La narration finale d'une question est toujours un peu bespoke ;
  un moteur ne produit pas d'insight, il produit des DataFrames.
- Schéma YAML prématuré, qui sera réécrit 3 fois.

L'équilibre choisi : **modularité forte + exécution explicite + manifest
comme documentation**.

---

## Ajouter une nouvelle question (Q4, Q5...)

1. Créer `src/questions/q4_<slug>.py` avec une classe et une variable `QUESTION`.
2. Ajouter une entrée dans `questions.yaml` (cf. template en bas du fichier).
3. Lancer : `python -m src.questions.runner --question Q4`.
4. Documenter dans `docs/02_research_questions.md`.
5. Ajouter une vue correspondante dans le dashboard si l'analyse est validée.

Aucun autre fichier à modifier. C'est le test de la modularité.
