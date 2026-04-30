# Bénin Risk Map

> **Un outil départemental de cartographie du risque opérationnel au Bénin, fondé sur 12 mois de signaux médiatiques mondiaux (GDELT), avec validation croisée et alertes personnalisables.**

Projet réalisé dans le cadre du **Hackathon iSHEERO × DataCamp Donates 2026 — Bénin Insights Challenge** par l'équipe Team09.

---

## Mission

Le Bénin absorbe un double choc — crise sécuritaire sahélienne au nord, recomposition diplomatique ouest-africaine — que les statistiques officielles ne mesurent pas. À partir de la base GDELT (Global Database of Events, Language and Tone), nous construisons la première cartographie départementale du risque opérationnel béninois sur 12 mois, à destination des ONG opérationnelles, de la presse sécurité, des décideurs publics et des ambassades.

## Les 3 questions de recherche

- **Q1 — Le terrain.** Comment se distribue le risque sécuritaire opérationnel département par département au Bénin sur 12 mois, comparé aux régions frontalières du Burkina Faso et du Niger ?
- **Q2 — Le ton.** Comment évolue le ton médiatique mondial sur le Bénin par domaine de risque (sécuritaire, économique, sanitaire, informationnel) sur 12 mois, et à quels narratifs les points de bascule sont-ils attribuables ?
- **Q3 — Le réseau.** Avec quels acteurs et médias le Bénin co-apparaît-il, comment cette structure se recompose-t-elle depuis juillet 2023, et quels médias portent quels narratifs ?

## Doctrine d'analyse

Nos quatre principes structurants (cf. [docs/01_doctrine.md](docs/01_doctrine.md)) :

1. **Story-as-unit** — l'unité d'analyse est la story (cluster d'articles), pas l'event brut.
2. **Confidence as slider** — toute analyse présentée en deux régimes (strict / large).
3. **Domains, not codes** — agrégation des codes CAMEO en 5-7 domaines de risque lisibles.
4. **Admin1-first** — maille géographique = département béninois, pas pays.

## Structure du repo

```
.
├── data/                # Données locales (gitignored sauf .gitkeep)
│   ├── raw/             # Extraits BigQuery bruts (Parquet)
│   ├── interim/         # Nettoyés, dédupliqués
│   ├── processed/       # Agrégats prêts pour viz/ML
│   ├── external/        # ACLED, GDELT Cloud, shapefiles
│   └── models/          # Artefacts ML entraînés
├── src/
│   ├── config.py        # Constantes (pays, fenêtre, paths, mappings)
│   ├── pipeline/        # Extraction, nettoyage, enrichissement, clustering stories
│   ├── analytics/       # Primitives pures (DataFrame -> DataFrame)
│   ├── ml/              # Wrappers de modèles entraînés (HF, sklearn)
│   ├── viz/             # Factories de figures Plotly
│   └── questions/       # Orchestrateurs Q1, Q2, Q3 + runner CLI
├── questions.yaml       # Manifest des questions de recherche
├── dashboard/           # App Streamlit (3 onglets)
│   ├── app.py
│   └── pages/
├── notebooks/           # Notebooks Jupyter d'analyse
├── reports/             # Pitch, résumé 1 page, figures finales
└── docs/                # Documentation interne d'équipe
```

L'architecture est documentée en détail dans [docs/04_architecture.md](docs/04_architecture.md).
Quatre couches en cascade (`pipeline` → `analytics`/`ml`/`viz` → `questions` →
consommateurs) garantissent la modularité et la testabilité.

## Installation et exécution

### 1. Prérequis

- Python 3.10+ recommandé
- Compte Google Cloud avec accès BigQuery (1 TB gratuit/mois)
- (Optionnel) Compte ACLED — https://developer.acleddata.com/
- (Optionnel) Compte GDELT Cloud free tier — https://gdeltcloud.com/

### 2. Configuration

```bash
git clone git@github.com:StephaneBah/GDELT_Challenge_Isheero_2026_Team09.git
cd GDELT_Challenge_Isheero_2026_Team09
python -m venv .venv
source .venv/bin/activate            # ou .venv\Scripts\activate sur Windows
pip install -r requirements.txt
cp .env.example .env                 # puis éditer .env avec vos credentials
```

Configurer Google Cloud :

1. Créer un service account sur https://console.cloud.google.com
2. Télécharger la clé JSON, la placer à la racine sous `gcp-credentials.json`
3. Renseigner `GOOGLE_APPLICATION_CREDENTIALS` et `GCP_PROJECT_ID` dans `.env`

### 3. Lancer le pipeline

Avec `make` (Linux/Mac, ou Git Bash sur Windows) :

```bash
make install               # installation des dépendances
make extract               # snapshot 12 mois (à exécuter une seule fois)
make process               # nettoyage + enrichissement + clustering stories
make questions-list        # liste les questions du manifest
make question Q=Q1         # exécute une question donnée
make dashboard             # lance le dashboard Streamlit
```

Sans `make` (PowerShell Windows) :

```powershell
pip install -r requirements.txt
python -m src.pipeline.extract
python -m src.pipeline.clean
python -m src.pipeline.enrich
python -m src.pipeline.stories
python -m src.questions.runner --list
python -m src.questions.runner --question Q1
streamlit run dashboard/app.py
```

### Ajouter une nouvelle question

1. Créer `src/questions/q4_<slug>.py` exposant une variable `QUESTION` qui
   respecte le protocole défini dans `src/questions/base.py`.
2. Ajouter une entrée dans [`questions.yaml`](questions.yaml) (template fourni).
3. Lancer `make question Q=Q4`.

Voir [docs/04_architecture.md](docs/04_architecture.md) pour les conventions
détaillées.

## Snapshot des données

L'extraction est figée sur l'**année calendaire 2025** (1er janvier → 31 décembre 2025), conformément à la consigne du hackathon. La date d'exécution exacte de l'extraction est inscrite dans `data/_metadata.json` au moment du snapshot.

> **Important** — toujours filtrer sur la partition `_PARTITIONTIME` en premier dans toute requête BigQuery pour préserver le quota mensuel de 1 TB.

## Usage d'IA (transparence — exigée par le hackathon)

- **Modèles ML locaux** : `xlm-roberta` (sentiment multilingue), `BERTopic` (clustering thématique), `sentence-transformers` (recherche sémantique). Tous open-source, exécutés localement, aucun coût d'API.
- **Assistance LLM pendant le développement** : Claude (Anthropic) a été utilisé en assistant de pair-programming pour la conception du pipeline, la rédaction de la documentation et l'aide à l'analyse. Les choix méthodologiques et les insights finaux relèvent de l'équipe.
- **Pas d'appel à des LLM commerciaux dans le pipeline de production**.

## Sources et crédits

Voir [CREDITS.md](CREDITS.md). En particulier :

- **GDELT Project** (Kalev Leetaru, Georgetown) — source primaire de données
- **GDELT-Events-Analysis** (reicHerr) — pipeline d'extraction adapté avec son accord
- **ACLED** — validation croisée des événements de conflit
- **GDELT Cloud** — couche d'inspiration produit (cf. doctrine)

## Licence

MIT — voir [LICENSE](LICENSE).
