# Les 3 questions de recherche

Cf. [01_doctrine.md](01_doctrine.md) pour les principes méthodologiques transverses.

---

## Q1 — Le terrain

> **Comment se distribue le risque sécuritaire opérationnel département par département au Bénin sur 12 mois ? Quels départements (Atacora, Alibori, Borgou…) connaissent quelle évolution, et comment leur trajectoire se compare-t-elle aux régions frontalières du Burkina Faso et du Niger ?**

### Variables GDELT mobilisées

| Champ | Usage |
|---|---|
| `SQLDATE`, `MonthYear` | Axe temporel |
| `EventRootCode` | Filtre 14, 18, 19, 20 (sécuritaire) |
| `EventCode` | Granularité fine (1822, 1831, 195, …) |
| `Actor1Type1Code`, `Actor2Type1Code` | Filtre acteurs (REB, MIL, CVL) |
| `ActionGeo_CountryCode` | BN, UV, NG |
| `ActionGeo_ADM1Code`, `dept_normalized` | Maille départementale |
| `GoldsteinScale` | Sévérité (-10 à +10) |
| `NumMentions` | Pondération |

### Méthodes

1. Carte choroplèthe par département (intensité = nombre de stories sécuritaires, couleur = sévérité moyenne).
2. Série temporelle par pays, lissée 7j, normalisée.
3. Boxplot `GoldsteinScale` BN/UV/NG.
4. Ratio `NumMentions / story` à GoldsteinScale équivalent — test de sous-couverture.

### ML

- Classification CAMEO → catégories lisibles avec random forest.
- Détection d'anomalies temporelles (PELT) sur la série Bénin.

### Insight visé (à valider)

> *« Sur 12 mois, le Bénin a enregistré N incidents sécuritaires concentrés à 75% dans Atacora et Alibori. Cette intensité représente Y% de celle observée au Burkina Faso, mais a généré Z fois moins de mentions médiatiques. La crise béninoise est statistiquement sous-couverte. »*

---

## Q2 — Le ton

> **Comment évolue le ton médiatique mondial sur le Bénin par domaine de risque (sécuritaire, économique, sanitaire, informationnel) sur 12 mois, et à quels narratifs (stories) les points de bascule sont-ils attribuables ?**

### Variables GDELT mobilisées

| Champ | Usage |
|---|---|
| `AvgTone` (events) | Ton moyen par event |
| `MentionDocTone` (mentions) | Ton détaillé par article |
| `V2Themes` (GKG) | Thèmes pour stratification |
| `risk_domain` (enrichi) | Stratification principale |

### Méthodes

1. Série temporelle du ton lissé (7j ou 14j), pondéré par NumMentions, par domaine.
2. Détection PELT/CUSUM des points de rupture (`src/ml/change_points.py`).
3. Pour chaque rupture : extraire les top stories des 7 jours précédents.
4. Comparaison ton FR vs EN (sous-échantillonnage par `MentionTimeDate` et `MentionSourceName`).

### ML

- xlm-roberta sur titres pour validation croisée AvgTone (`src/ml/sentiment.py`).
- BERTopic pour identification automatique des thèmes par cluster temporel.

### Insight visé

> *« Le ton mondial sur le Bénin connaît N ruptures sur 12 mois. La plus marquée (mois M) coïncide avec [story]. Le ton sécuritaire est en dégradation continue (-X points), tandis que le ton économique reste stable. »*

---

## Q3 — Le réseau

> **Avec quels acteurs (États, organisations, personnalités) le Bénin co-apparaît-il dans la presse mondiale, comment cette structure se recompose-t-elle depuis juillet 2023 (rupture CEDEAO/AES), et quels médias portent quels narratifs ?**

### Variables GDELT mobilisées

| Champ | Usage |
|---|---|
| `Actor1Code/Name`, `Actor2Code/Name` | Acteurs |
| `Actor1Type1Code`, `Actor2Type1Code` | Filtre GOV, MIL, IGO, NGO |
| `MentionSourceName` (mentions) | Top médias |
| `QuadClass`, `GoldsteinScale` | Polarité des relations |
| `SQLDATE` | Découpage pré/post juillet 2023 |

### Méthodes

1. Construire graphe d'acteurs sur stories Bénin (`src/ml/network.py`).
2. Communautés Louvain.
3. Comparer pré-juillet 2023 vs post-juillet 2023 : variation du degré pondéré par acteur.
4. Graphe bipartite acteurs ↔ médias : qui parle de qui ?

### ML

- Détection de communautés (Louvain).
- Optionnel : embeddings d'acteurs (Node2Vec) pour mesurer distance diplomatique.

### Insight visé

> *« Depuis juillet 2023, la co-occurrence Bénin–Niger a chuté de X%, tandis que Bénin–[Y] a doublé. Le ton bilatéral Bénin-Niger est passé de A à B sur l'échelle Goldstein. La position diplomatique observable du Bénin se cristallise autour de [pôle]. »*

---

## Synthèse

| Q | Maille | Variable principale | Visualisation phare | Profil leader |
|---|---|---|---|---|
| Q1 | département | volume + sévérité (stories) | carte choroplèthe + comparaison BN/UV/NG | DA + MLE |
| Q2 | domaine de risque | ton lissé par story | série temporelle + ruptures détectées | MLE + DA |
| Q3 | acteur + média | co-occurrence pondérée | graphe bipartite évolutif | MLE + DS |

Les 5 insights du pitch dérivent directement de ces 3 questions.
