"""
Données de démo — utilisées quand ANTHROPIC_API_KEY est absente ou solde épuisé.
Simule une session complète sur le secteur Diplomatie.
"""

DEMO_SUMMARY = {
    "total_events": 9911,
    "date_range": {"min": "2025-01-01", "max": "2025-12-31"},
    "avg_tone": -0.84,
    "avg_goldstein": 1.73,
    "avg_tension": 44.2,
    "coop_pct": 58.3,
    "conflict_pct": 12.1,
    "economic_pct": 8.7,
    "top_themes": {
        "Consultations diplomatiques": 6476,
        "Coopération diplomatique": 3435,
        "Déclarations publiques": 2981,
        "Appels & Demandes": 1624,
        "Combats armés": 1482,
        "Désapprobations": 1234,
        "Coopération matérielle": 636,
        "Aide fournie": 837,
    },
    "top_actors": {
        "France": 1243,
        "États-Unis": 987,
        "Nigeria": 654,
        "Chine": 543,
        "Union Européenne": 421,
        "Côte d'Ivoire": 312,
        "Allemagne": 287,
        "ONU": 265,
    },
    "anomaly_months": ["2025-04-01", "2025-09-01"],
    "monthly_evolution": [
        {"month": "2025-01-01", "count": 720, "avg_tone": -0.6, "avg_gold": 1.9, "avg_tension": 41.0},
        {"month": "2025-02-01", "count": 698, "avg_tone": -0.7, "avg_gold": 1.8, "avg_tension": 42.0},
        {"month": "2025-03-01", "count": 810, "avg_tone": -0.5, "avg_gold": 2.1, "avg_tension": 39.5},
        {"month": "2025-04-01", "count": 1240, "avg_tone": -2.1, "avg_gold": 0.4, "avg_tension": 61.2},
        {"month": "2025-05-01", "count": 756, "avg_tone": -0.9, "avg_gold": 1.6, "avg_tension": 44.8},
        {"month": "2025-06-01", "count": 834, "avg_tone": -0.4, "avg_gold": 2.3, "avg_tension": 38.7},
        {"month": "2025-07-01", "count": 792, "avg_tone": -0.8, "avg_gold": 1.7, "avg_tension": 43.1},
        {"month": "2025-08-01", "count": 880, "avg_tone": -1.1, "avg_gold": 1.4, "avg_tension": 46.5},
        {"month": "2025-09-01", "count": 1380, "avg_tone": -2.8, "avg_gold": -0.3, "avg_tension": 67.4},
        {"month": "2025-10-01", "count": 810, "avg_tone": -0.7, "avg_gold": 1.8, "avg_tension": 42.9},
        {"month": "2025-11-01", "count": 756, "avg_tone": -0.6, "avg_gold": 1.9, "avg_tension": 41.3},
        {"month": "2025-12-01", "count": 735, "avg_tone": -0.5, "avg_gold": 2.0, "avg_tension": 40.1},
    ],
}

DEMO_INTENT = {
    "keywords": ["diplomatie", "france", "cooperation"],
    "intent_fr": "Analyse de la couverture diplomatique internationale du Bénin en 2025",
    "data_focus": "diplomatie",
}

DEMO_REPORT1 = """## Tendances clés

La couverture médiatique diplomatique du Bénin en 2025 repose sur **9 911 événements** avec un ton légèrement négatif (−0,84) et un score de stabilité positif (+1,73), signalant une posture internationale **globalement constructive** mais sous tension ponctuelle.

Le volume mensuel oscille entre 698 et 880 événements en régime normal. **Deux pics majeurs** se détachent : avril (+72% vs moyenne) et septembre (+91%), classés comme anomalies par l'analyse statistique.

## Thèmes dominants

Les **consultations diplomatiques** (6 476 événements, 65% du volume) dominent massivement, traduisant une diplomatie béninoise active centrée sur le dialogue bilatéral. La **coopération diplomatique formelle** (3 435 événements) confirme que ces consultations aboutissent fréquemment à des engagements concrets.

Le ratio coopération/conflit de **4,8:1** est favorable, mais les 1 482 événements de type "Combats armés" dans la couverture associée indiquent que le contexte sécuritaire régional reste un angle éditorial récurrent.

## Anomalies détectées

**Avril 2025** : +72% de volume, chute du ton à −2,1 et du Goldstein à +0,4. Rupture nette par rapport à la tendance. Probable couverture d'une crise diplomatique ou d'un événement régional majeur.

**Septembre 2025** : pic le plus intense de l'année (+91%, ton −2,8, Goldstein −0,3). Seul mois avec un score de stabilité négatif — signal d'un épisode déstabilisant couvert massivement par la presse internationale.

## Lecture stratégique

Le Bénin affiche un profil diplomatique **actif et reconnu** par les médias mondiaux, avec la France, les États-Unis et la Chine comme partenaires les plus couverts. Les deux anomalies d'avril et septembre méritent une investigation croisée des sources pour identifier les événements déclencheurs.
"""

DEMO_REPORT2 = """## Ce que disent les médias

Les articles sources révèlent une couverture concentrée sur **trois registres** : les visites officielles de haut niveau (présidence, ministères), les accords de coopération économique et sécuritaire avec les partenaires occidentaux, et la question sécuritaire au nord du pays liée aux dynamiques sahéliennes.

La France reste le pays dont les médias couvrent le plus intensément le Bénin — essentiellement *Le Monde Afrique*, *RFI* et *France 24* — avec un angle qui oscille entre coopération au développement et enjeux sécuritaires.

## Explication des irrégularités

Le pic d'**avril** correspond à une période de tension diplomatique régionale autour de la frontière nord (Burkina Faso, Niger). Les articles montrent une multiplication des déclarations officielles et des prises de position publiques du gouvernement béninois, capturées massivement par GDELT.

**Septembre** coïncide avec l'Assemblée Générale de l'ONU — moment où le Bénin multiplie les rencontres bilatérales, générant un volume exceptionnel d'événements CAMEO de type consultation et coopération, avec un ton plus critique lié aux débats sur la souveraineté et l'aide internationale.

## Angle éditorial

La couverture est majoritairement **francophone et occidentale**. Les médias africains (presse locale, médias panafricains) sont sous-représentés dans le dataset GDELT pour le Bénin, ce qui introduit un biais de perspective à considérer dans l'interprétation des scores de ton.
"""

DEMO_SUGGESTIONS = [
    "Quels acteurs dominent les échanges en septembre ?",
    "Comment évolue la coopération avec la France ?",
    "Y a-t-il un lien entre tension sécuritaire et ton médiatique ?",
]

DEMO_FOLLOWUP = """En septembre 2025, les **acteurs gouvernementaux (GOV)** représentent 67% des événements du mois — bien au-dessus de leur part annuelle de 54%. C'est le signe que la couverture médiatique de ce mois est essentiellement centrée sur les interactions au niveau étatique.

La délégation béninoise à l'**Assemblée Générale de l'ONU** (New York, 16-30 septembre) concentre une part importante : les consultations multilatérales y génèrent mécaniquement un pic GDELT, car chaque rencontre bilatérale en marge de l'AG est codée comme un événement distinct.

Les acteurs militaires (MIL) progressent également en septembre (+18% vs moyenne), reflétant la couverture des questions sécuritaires dans les discours officiels. Le Goldstein négatif (−0,3) de ce mois s'explique davantage par le registre rhétorique des déclarations (ton de revendication, demandes de soutien) que par des actes de violence réels.

**Conclusion** : le pic de septembre est structurellement lié au calendrier diplomatique onusien, non à une crise. C'est une anomalie de contexte, pas de contenu.
"""
