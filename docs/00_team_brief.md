# Brief équipe — Bénin Insights Challenge 2026

**Lecture : 5 min · Réunion : 30 min · À valider aujourd'hui**

---

## 1. Le défi en 30 secondes

GDELT surveille les médias mondiaux dans 100+ langues. Notre mission : en extraire **tout ce qui concerne le Bénin sur 12 mois**, le transformer en **5 insights utiles** à un journaliste / chercheur / décideur public, et porter le tout dans un dashboard + un pitch de 3 minutes.

**Deadline Phase 1 : mardi 5 mai · 23h59.** On a 7 jours.

**Ce n'est pas un concours de code.** L'évaluation est : insights 25% · technique 25% · dashboard 20% · reproductibilité 15% · pitch 15%. **65% du score dépend de la narration.**

---

## 2. La vision projet

> **« Bénin Risk Map — un outil départemental de cartographie du risque opérationnel, fondé sur 12 mois de signaux médiatiques mondiaux, avec validation croisée et alertes personnalisables. »**

Le Bénin absorbe un double choc — crise sécuritaire sahélienne au nord, recomposition diplomatique ouest-africaine — que les statistiques officielles ne mesurent pas. Notre projet construit la **première cartographie départementale du risque opérationnel béninois** à partir des signaux médiatiques mondiaux captés par GDELT.

**Public cible** : ONG opérationnelles au nord, presse sécurité et data-journalisme, décideurs publics CEDEAO/UE, ambassades, assureurs-crédit pays.

---

## 3. Pourquoi cet angle (et pas un autre)

| Critère | Verdict |
|---|---|
| Pertinence locale | ✅ Sujets brûlants, sous-couverts internationalement |
| Force GDELT | ✅ Events table + actor network = ses meilleures cartes |
| Surprise possible | ✅ Latence médiatique, bascule de ton, recomposition silencieuse |
| Actionnabilité | ✅ Public clair : journalistes sécurité, ONG, décideurs |
| Faisabilité 7j | ✅ Périmètre cadré, pas d'exploration tous azimuts |

**Alternative envisagée** : focaliser sur l'élection présidentielle 2026. Plus grand public, mais plus risqué politiquement et déjà très couvert par d'autres équipes potentielles. À discuter.

---

## 4. État de l'art et positionnement

GDELT a été créée en 2013 par **Kalev Leetaru** (Georgetown). Sa réputation s'est construite sur deux familles d'usage : la **prévision précoce de crises** (depuis l'analyse fondatrice du Printemps arabe) et la **mesure de signaux qu'aucune statistique officielle ne capte** (ton international, réseau diplomatique observable, sous-couverture médiatique).

**Domaines où GDELT a déjà fait ses preuves** :
- Forecasting d'instabilité politique et de coups d'État (système **ICEWS** du Département d'État américain, travaux de Philip Schrodt et Jay Goldstone)
- Monitoring d'insurrections — abondamment utilisé sur **Boko Haram** (Lac Tchad) et le **Sahel central** (Mali / Burkina / Niger)
- Cartographie de la couverture asymétrique des crises (journalisme data : Reuters Institute, NYT, Quartz, Bellingcat)
- Analyse des recompositions diplomatiques (notamment investissements chinois en Afrique post-2013, Belt and Road)
- Détection précoce d'épidémies (Ebola 2014, COVID-19)
- Monitoring humanitaire (UN Global Pulse, World Bank fragility)

**Limites documentées qu'on doit traiter méthodologiquement** :
1. **Géocodage infranational imprécis** (Hammond & Weidmann 2014) — vérifier sur échantillon, rester prudents sur les cartes au-delà du niveau ADM1.
2. **Sur-comptage d'événements** — toujours pondérer ou dédupliquer par `NumMentions`.
3. **Biais anglophone** dans le crawl malgré 100+ langues — à documenter explicitement dans le rapport.
4. **`AvgTone` est un signal grossier** (calculé par dictionnaire GCAM) — valider sur sous-échantillon avec un modèle moderne (xlm-roberta).
5. **Codes acteurs bruyants** — filtrer par `Actor1Type1Code` (GOV, MIL, IGO, NGO) pour rester sur l'analyse politique.

**Compagnon obligatoire — ACLED** (Armed Conflict Location & Event Data) : base curée manuellement, référence académique en Afrique. Croiser GDELT ↔ ACLED sur 1-2 cas concrets (par ex. attaques au nord du Bénin) coûte peu et démultiplie la crédibilité du jury.

**Notre proposition de valeur**, à porter dans le pitch :
> *Première analyse GDELT structurée du cas béninois, en miroir comparatif avec ses voisins sahéliens, avec validation croisée sur ACLED.*

À notre connaissance, aucune étude majeure GDELT-Bénin n'a été publiée — Burkina, Mali, Niger, Nigeria sont abondamment couverts, mais le Bénin reste un angle mort. **La méthode est éprouvée, le terrain est neuf** : c'est notre originalité.

---

## 5. Doctrine d'analyse — 4 principes structurants

Inspirée des choix produits faits par GDELT Cloud (couche commerciale d'enrichissement de GDELT), notre méthodologie repose sur 4 décisions transverses qui s'appliquent à l'extraction, au ML, au dashboard et au pitch.

1. **Story-as-unit** — l'unité d'analyse est la *story* (cluster d'articles racontant le même fait), pas l'event brut. Divise le bruit par ~10, rend les comptages crédibles. Construite par le ML Engineer (TF-IDF + DBSCAN ou BERTopic).
2. **Confidence as slider** — toute analyse est présentée en deux régimes (strict / large), exposant le bruit à l'utilisateur via un curseur dans le dashboard. Anticipe la question critique du jury sur la qualité du signal.
3. **Domains, not codes** — on agrège les codes CAMEO en 5-7 **domaines de risque** lisibles : sécuritaire, économique, sanitaire, informationnel, environnemental, politique, infrastructurel. Le langage de l'interface est celui d'un analyste, pas d'un codeur GDELT.
4. **Admin1-first** — la maille géographique de référence est le **département** (12 départements béninois), jamais le pays seul. Cartes choroplèthes par défaut. Audit de la qualité du géocodage `ActionGeo_ADM1Code` dès l'extraction.

---

## 6. Les 3 questions de recherche

> **Q1 — Le terrain.** Comment se distribue le **risque sécuritaire opérationnel département par département** au Bénin sur 12 mois ? Quels départements (Atacora, Alibori, Borgou…) connaissent quelle évolution, et comment leur trajectoire se compare-t-elle aux régions frontalières du Burkina Faso et du Niger ?

> **Q2 — Le ton.** Comment évolue le **ton médiatique mondial sur le Bénin par domaine de risque** (sécuritaire, économique, sanitaire, informationnel) sur 12 mois, et à quels narratifs (stories) les points de bascule sont-ils attribuables ?

> **Q3 — Le réseau.** Avec quels acteurs (États, organisations, personnalités) le Bénin co-apparaît-il dans la presse mondiale, comment cette structure se recompose-t-elle depuis juillet 2023 (rupture CEDEAO/AES), et **quels médias portent quels narratifs** ?

| Q | Maille | Variable principale | Visualisation phare |
|---|---|---|---|
| Q1 | département | volume + sévérité d'incidents (stories) | carte choroplèthe + comparaison BN / UV / NG |
| Q2 | domaine de risque | ton (`AvgTone` lissé par story) | série temporelle multi-courbes + ruptures détectées |
| Q3 | acteur + média | co-occurrence pondérée | graphe bipartite évolutif (avant/après juillet 2023) |

Chaque question alimente une visualisation distincte et un insight du pitch.

---

## 7. Répartition par profil

| Profil | Mission Phase 1 |
|---|---|
| **Data Engineer** | Pipeline BigQuery → Parquet local. Extraction events + mentions + GKG sur **3 pays** (BN, UV, NG) sur 12 mois. Mapping CAMEO → 5-7 domaines de risque. Audit géocodage admin1 sur le Bénin. Script reproductible en une commande. |
| **Data Analyst** | EDA, séries temporelles **par domaine de risque**, carte choroplèthe par département, top acteurs / médias. ≥5 visualisations commentées. Maquette des 3 onglets du dashboard (Tableau de bord / Explorer / Méthodologie). |
| **ML Engineer** | (a) **Clustering events → stories** (TF-IDF + DBSCAN ou BERTopic), (b) sentiment multilingue (xlm-roberta) sur titres, (c) détection de points de bascule (PELT / `ruptures`) sur séries de ton, (d) graphe d'acteurs + community detection (Louvain). Métriques + baselines obligatoires. |
| **Data Scientist** | Coordination des questions, interprétation, validation croisée ACLED + GDELT Cloud, rédaction des 5 insights, narration pitch + résumé 1 page. Challenge la qualité des résultats. |

**Règle d'or** : on commit dès le jour 1 sur GitHub, on travaille par branches, on documente au fur et à mesure.

---

## 8. Calendrier 7 jours

| Jour | Objectif |
|---|---|
| Mar 28 (auj.) | Réunion cadrage · setup repo · validation angle |
| Mer 29 | Pipeline GDELT v1 opérationnel · 1ère extraction Bénin |
| Jeu 30 | **Office Hours iSHEERO** · EDA + premières viz |
| Ven 1 mai | Modèle ML v1 · viz dashboard v1 |
| Sam 2 | Itération insights · dashboard v2 |
| Dim 3 | Dashboard final · draft pitch · résumé 1 page |
| Lun 4 | **Buffer** · tournage vidéo · QA repro README |
| Mar 5 | Soumission |

---

## 9. Décisions à valider aujourd'hui

1. **Vision validée** (Bénin Risk Map) ou bascule-t-on sur Élection 2026 ?
2. **Doctrine d'analyse** (story-as-unit · confidence-slider · domains-not-codes · admin1-first) — on adopte les 4 principes ?
3. **Les 3 questions raffinées** : on garde telles quelles ?
4. **Validation croisée ACLED + GDELT Cloud free tier** : on s'engage à intégrer ces deux vérifications sur 1-2 cas ? (recommandé)
5. **Stack technique** : BigQuery + Python (Pandas/Polars) + Streamlit Cloud + scikit-learn + HuggingFace + NetworkX ?
6. **Repo GitHub** : déjà cloné — `StephaneBah/GDELT_Challenge_Isheero_2026_Team09` ✅
7. **Outil de coordination** : Notion / Google Docs / Discord ?

Une fois ces points actés, chacun a sa roadmap claire et on n'y revient plus.
