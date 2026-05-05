# Bénin Risk Map — Résumé d'une page

**Hackathon iSHEERO × DataCamp Donates 2026 · Équipe Team09**

> *La première cartographie départementale du risque opérationnel béninois,
> à partir de 12 mois de signaux médiatiques mondiaux GDELT, avec validation
> croisée et alertes personnalisables.*

---

## Le problème

Le Bénin absorbe en silence un double choc en 2025 : la crise sécuritaire
sahélienne qui déborde du Burkina Faso et du Niger vers les départements
frontaliers du nord (Atacora, Alibori), et la recomposition diplomatique
ouest-africaine post-rupture CEDEAO/AES. Les statistiques officielles ne
mesurent ni l'un, ni l'autre. Les médias internationaux y consacrent une
attention disproportionnellement faible par rapport à ses voisins.

## Notre approche

À partir de la base GDELT (Global Database of Events, Language and Tone) sur
l'année calendaire 2025, nous avons :

1. **Extrait** tous les events concernant le Bénin, le Burkina Faso et le
   Niger (~__N__ events, validation croisée avec ACLED).
2. **Enrichi** chaque event avec un *domaine de risque* lisible (sécuritaire,
   politique, économique, humanitaire) plutôt qu'un code CAMEO opaque.
3. **Clusterisé** les events en *stories* pour éliminer le sur-comptage
   inhérent à GDELT (un fait = N articles = N events bruts, donc 1 story).
4. **Modélisé** le ton via xlm-roberta multilingue pour valider le signal
   `AvgTone` natif de GDELT.
5. **Cartographié** le risque par département béninois (12 départements).

## Cinq insights clés

> *Les valeurs ci-dessous sont à remplir avec les chiffres réels produits par les modules `src.questions.q1_terrain`, `q2_tone`, `q3_network`. Voir le notebook `notebooks/01_exploration.ipynb` pour les calculs.*

1. **__INSIGHT 1 — Sous-couverture__**
   Un event sécuritaire au Bénin génère __X__× moins de mentions médiatiques
   mondiales qu'un event comparable au Burkina Faso. Le Bénin est un angle
   mort de la couverture sahélienne.

2. **__INSIGHT 2 — Concentration géographique__**
   Le risque sécuritaire opérationnel au Bénin est concentré à **__Y%__**
   dans les départements de l'__Atacora__ et de l'__Alibori__, frontaliers
   du Burkina Faso et du Niger.

3. **__INSIGHT 3 — Bascule narrative__**
   Le ton mondial sur le Bénin connaît **__N__ ruptures statistiques** sur
   2025, dont la plus marquée (le __DATE__) coïncide avec __[story]__.

4. **__INSIGHT 4 — Recomposition diplomatique__**
   Depuis juillet 2023 (rupture CEDEAO/AES), la co-occurrence médiatique
   Bénin–Niger a chuté de **__X%__**, tandis que la co-occurrence Bénin–
   __[acteur Y]__ a doublé.

5. **__INSIGHT 5 — Asymétrie sectorielle__**
   Le ton sur le **risque sécuritaire** béninois se dégrade continûment
   (-__Z__ points sur 12 mois) alors que le ton sur le **risque économique**
   reste stable, voire s'améliore. Les deux récits coexistent sans se croiser.

## À qui ça sert

- **ONG opérationnelles** au nord du Bénin — calibrer leur exposition
  sécuritaire et leurs zones d'intervention.
- **Presse sécurité et data-journalisme** — accéder à un signal continu et
  comparable sur un terrain peu couvert.
- **Décideurs publics** (CEDEAO, UE, ambassades) — disposer d'une mesure
  indépendante de la perception internationale.
- **Assureurs-crédit pays** — affiner leur évaluation du risque-pays Bénin
  par département.

## Reproductibilité et open-source

Tout le code est sur GitHub
([StephaneBah/GDELT_Challenge_Isheero_2026_Team09](https://github.com/StephaneBah/GDELT_Challenge_Isheero_2026_Team09)),
sous licence MIT. Le pipeline complet se rejoue en deux commandes
(`make extract && make process`). Le dashboard est accessible en ligne sur
Streamlit Cloud (lien dans le README).

**Architecture** : 4 couches modulaires (pipeline → analytics/ml/viz →
questions → consommateurs). Ajouter une nouvelle question = ajouter un
fichier `src/questions/q4_*.py` + une entrée dans `questions.yaml`.

**Crédits** : code de pipeline initial adapté de
[reicHerr/GDELT-Events-Analysis](https://github.com/reicHerr/GDELT-Events-Analysis)
(MIT). Validation croisée sur ACLED. Inspiration produit : GDELT Cloud.
