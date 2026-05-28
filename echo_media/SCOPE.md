# Echo Média — Scope & Vision

## Concept

**"Chat with your GDELT data"**

L'utilisateur ne cherche plus — il dialogue. Echo Média transforme l'empreinte médiatique du Bénin en une expérience conversationnelle sur mesure. Pas de filtres à manipuler, pas de graphes à déchiffrer seul : le système s'adapte au profil et à la vision de chaque utilisateur.

---

## Problème résolu

Les données GDELT sont riches mais opaques. Aujourd'hui pour en tirer de la valeur il faut :
- Savoir quels filtres appliquer
- Comprendre les codes CAMEO
- Interpréter soi-même les tendances et anomalies

Echo Média efface ce friction et rend la donnée accessible à n'importe quel profil (journaliste, investisseur, chercheur, décideur politique).

---

## Expérience utilisateur

### Acte 1 — L'entrée
Page épurée. Centré. Deux choix :
- Sélectionner un secteur d'intérêt (Économie, Diplomatie, Conflits, Tourisme, Partenariats, Libre)
- Ou directement poser une question dans le chat

Pas un graphe en vue. Juste l'intention de l'utilisateur.

### Acte 2 — Le filet
Le système comprend l'intention → filtre les données GDELT → sort les premiers visuels pertinents (volume, ton médiatique, thèmes dominants).

En parallèle à droite : un **mini-rapport automatique** en deux parties :
- **Rapport 1** — Tendances & anomalies détectées dans les données filtrées
- **Rapport 2** — Enrichissement : lecture des articles sources (URLs GDELT) croisée avec contexte externe → interprétation éditoriale

### Acte 3 — La conversation
Le système propose 3 questions pour continuer. L'utilisateur peut aussi poser librement la sienne. Chaque échange relance le pipeline sur le slice actif : nouveaux visuels, nouveau rapport.

L'affichage ressemble à une **conversation avec la donnée**, pas à un tableau de bord.

---

## Architecture technique

### Backend — FastAPI (Python)
- Garde toute la logique pandas/GDELT existante
- Endpoints REST + streaming SSE pour les rapports IA
- Claude API pour : extraction d'intention, génération de rapports, suggestions

### Frontend — HTML/CSS/JS vanilla (ou React si temps)
- Design custom : typographie soignée, dark mode, animations légères
- Pas de framework CSS lourd — contrôle total sur le visuel
- Plotly.js pour les graphiques côté client

### IA — Claude (Anthropic API)
- **Haiku** : extraction d'intention utilisateur (rapide, pas cher)
- **Sonnet** : génération des rapports et suggestions de conversation
- Streaming de la réponse pour effet "live typing"

### Données
- `GDELT_events_benin_2025_cleaned.csv` — dataset principal
- Filtrage pandas en mémoire (< 1s sur ce volume)
- Scraping léger des top 3 URLs sources pour le Rapport 2

---

## Ce qu'on ne fait PAS (scope prototype 6h)

- Pas d'authentification / profils utilisateurs
- Pas de base de données (tout en mémoire)
- Pas de déploiement cloud (demo locale)
- Pas de scraping massif (max 3 URLs par session)
- Pas de mémoire conversationnelle persistante (session uniquement)

---

## Métriques de succès (pitch)

1. L'utilisateur arrive sans contexte et obtient des insights pertinents en < 30 secondes
2. Les visuels reflètent exactement l'intention tapée (pas de résultats génériques)
3. Le rapport détecte au moins une anomalie réelle dans les données
4. La conversation peut continuer au moins 3 échanges de manière cohérente

---

## Structure du dossier

```
echo_media/
├── SCOPE.md              ← ce fichier
├── api/
│   ├── main.py           ← FastAPI app
│   ├── data_service.py   ← chargement + filtrage pandas
│   ├── ai_service.py     ← Claude API (intent, reports, suggestions)
│   └── scraper.py        ← lecture légère des URLs sources
├── frontend/
│   ├── index.html        ← page principale
│   ├── style.css         ← design system custom
│   └── app.js            ← logique UI + appels API
└── requirements.txt
```

---

## Ressources minimales

| Composant | Coût estimé par session |
|-----------|------------------------|
| Intent extraction (Haiku) | ~0.001$ |
| Rapport 1 — données (Sonnet) | ~0.01$ |
| Rapport 2 — URLs (Sonnet) | ~0.02$ |
| Suggestions follow-up (Haiku) | ~0.001$ |
| **Total par session complète** | **~0.03$** |

Optimisations :
- Résumé statistique du dataframe (pas les 8k lignes) envoyé au LLM
- Cache du chargement CSV (une seule fois au démarrage)
- Streaming SSE pour éviter les timeouts
