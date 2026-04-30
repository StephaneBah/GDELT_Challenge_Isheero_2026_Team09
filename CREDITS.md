# Crédits et attributions

Ce projet a été rendu possible grâce aux ressources et travaux suivants.

## Source primaire de données

**GDELT Project** (Global Database of Events, Language and Tone)
- Site : https://www.gdeltproject.org/
- Initiateur : Kalev Leetaru (Georgetown University)
- Données accédées via Google BigQuery : `gdelt-bq.gdeltv2.events_partitioned`, `gdelt-bq.gdeltv2.eventmentions_partitioned`, `gdelt-bq.gdeltv2.gkg_partitioned`
- Licence GDELT : libre et gratuit, sans restriction d'usage

## Code adapté

**GDELT-Events-Analysis** par reicHerr
- Repo : https://github.com/reicHerr/GDELT-Events-Analysis
- Licence : MIT
- Composants adaptés dans notre projet (`src/pipeline/`) :
  - `auth.py` — adaptation de `setup_authentication.py`
  - `bigquery_client.py` — adaptation de `initialize_client.py` et `extract_table.py`
- Modifications principales : extension à 3 pays (Bénin, Burkina Faso, Niger), filtre 12 mois, sortie Parquet (au lieu de CSV/SQLite), suppression de tout secret en clair, intégration au layout `src/`.

## Validation croisée

**ACLED** (Armed Conflict Location & Event Data Project)
- Site : https://acleddata.com/
- Référence académique pour les données de conflit en Afrique
- Utilisé pour la validation de notre cartographie sécuritaire (Q1) sur des cas concrets

**GDELT Cloud** (couche d'enrichissement commerciale de GDELT)
- Site : https://gdeltcloud.com/
- Free tier utilisé pour validation ponctuelle (Conflict Events, méthodologie ACLED) et inspiration des choix produits (cf. doctrine d'analyse).

## Modèles open-source

- **xlm-roberta-base / xlm-roberta-base-sentiment** (HuggingFace) — sentiment multilingue
- **BERTopic** — clustering thématique
- **sentence-transformers** (`paraphrase-multilingual-MiniLM-L12-v2` ou équivalent) — recherche sémantique
- **scikit-learn** — clustering, métriques
- **NetworkX** + **python-louvain** — analyse de réseaux et détection de communautés
- **ruptures** — détection de points de bascule

## Inspiration méthodologique

Cf. [docs/01_doctrine.md](docs/01_doctrine.md). Plusieurs choix de modélisation s'inspirent ouvertement de ce que GDELT Cloud expose comme bonnes pratiques produit :

- **Story-as-unit** : leur clustering events → stories, qui résout le sur-comptage GDELT.
- **Confidence as slider** : leur paramètre `confidence_profile=precise|loose`.
- **Domains, not codes** : leur taxonomie CAMEO+ (politique, économique, technologique, infrastructurel, sanitaire, informationnel, environnemental).
- **Admin1-first** : leur exposition d'admin1 comme filtre de première classe.

## Hackathon

**iSHEERO × DataCamp Donates — Bénin Insights Challenge 2026**
- Site iSHEERO : https://isheero.com/
- DataCamp Donates : https://www.datacamp.com/donates
- Calendrier officiel : 27 avril → 9 mai 2026

## Équipe Team09

- Data Engineer · _à compléter_
- Data Analyst · _à compléter_
- ML Engineer · _à compléter_
- Data Scientist · _à compléter_
