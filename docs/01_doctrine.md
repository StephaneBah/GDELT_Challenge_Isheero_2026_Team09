# Doctrine d'analyse — les 4 principes structurants

> Inspirés des choix produits faits par GDELT Cloud (couche commerciale d'enrichissement de GDELT) et adaptés à notre contexte hackathon. Ces principes guident l'extraction, le ML, le dashboard et le pitch.

---

## 1. Story-as-unit

**Principe** — l'unité d'analyse est la **story** (cluster d'articles racontant le même fait), pas l'event GDELT brut.

**Pourquoi** — GDELT renvoie un event par article. Une attaque rapportée par 350 médias devient 350 lignes. Tout comptage naïf est inflationniste, toute moyenne est biaisée. GDELT Cloud résout cela en exposant des « stories ». On reproduit la logique localement.

**Comment** — `src/pipeline/stories.py` opère un clustering rule-based simple (jour + EventRootCode + admin1 + acteurs). Le ML Engineer peut le raffiner avec BERTopic ou DBSCAN sur embeddings de titres.

**Conséquence chiffrée attendue** — réduction du volume d'un facteur ~5 à 10×. Une carte montrant « 50 incidents au nord du Bénin » devient lisible et juste, plutôt que « 500 events » incluant les doublons.

---

## 2. Confidence as slider

**Principe** — toute analyse est présentée en **deux régimes** (strict / large), exposés via un curseur dans le dashboard.

**Pourquoi** — GDELT est bruyant. Plutôt que de masquer ce bruit ou de l'imposer à l'utilisateur, on lui donne le contrôle. Décision honnête méthodologiquement, et anticipation directe de la question critique du jury.

**Critères** :
- **Strict** : NumSources ≥ 3 ET géolocalisation renseignée (lat/long).
- **Large** : tout passe.

**Implementation** — colonne `confidence_tier` dans `events_enriched.parquet`, ajoutée par `src/pipeline/enrich.py`. Dashboard expose un radio-button.

---

## 3. Domains, not codes

**Principe** — agrégation des codes CAMEO en **5-7 domaines de risque** lisibles : sécuritaire, politique, économique, humanitaire, informationnel, environnemental, infrastructurel.

**Pourquoi** — un analyste ne pense pas en codes. Il pense en domaines. *« 12 events de root code 19 »* ne dit rien à un journaliste. *« 12 incidents de risque sécuritaire »* parle.

**Mapping** — voir [03_cameo_domains_mapping.md](03_cameo_domains_mapping.md). Implémenté dans `src/config.py` (`CAMEO_TO_DOMAIN`) et appliqué par `src/pipeline/enrich.py`.

**Conséquence interface** — toutes les visualisations, tous les titres de section, tous les filtres parlent le langage des domaines. Les codes CAMEO bruts apparaissent uniquement dans l'onglet Méthodologie (pour les data-curieux).

---

## 4. Admin1-first

**Principe** — la maille géographique de référence est le **département béninois** (12 départements), jamais le pays seul.

**Pourquoi** — *« Bénin »* à l'échelle pays est trop grossier pour un outil opérationnel. La carte de risque par département est précisément ce que demandent les ONG, les ambassades, les journalistes.

**Les 12 départements** :
Alibori, Atacora, Atlantique, Borgou, Collines, Couffo, Donga, Littoral, Mono, Ouémé, Plateau, Zou.

**Implémentation** — colonne `dept_normalized` dans `events_enriched.parquet`, normalisée à partir de `ActionGeo_FullName` et `ActionGeo_ADM1Code`. **Audit obligatoire en day 1** sur un échantillon — si le géocodage GDELT est trop creux, fallback sur reverse geocoding via `ActionGeo_Lat/Long` + shapefile officiel.

**Visualisation par défaut** — carte choroplèthe des 12 départements, colorée par intensité du domaine de risque sélectionné.

---

## Application transverse

| Phase | Story-as-unit | Confidence slider | Domains | Admin1 |
|---|---|---|---|---|
| Extraction | Préserver `NumMentions`, `NumSources` | Préserver tous les champs nécessaires au tri | Garder `EventRootCode` ET `EventCode` | Garder `ActionGeo_*` complet |
| Enrichissement | Cluster events -> stories | Calcul `confidence_tier` | Mapping CAMEO -> `risk_domain` | Normalisation `dept_normalized` |
| ML | Modéliser sur stories | Reporter métriques par tier | Stratifier par domaine | Modèles par département |
| Dashboard | Compteurs en stories | Radio strict/large dans sidebar | Filtres et titres en domaines | Carte choroplèthe par défaut |
| Pitch | « N incidents » et non « N events » | Mentionner les deux régimes | Langage domaine | Insights géographiques départementaux |
