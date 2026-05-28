# Echo Média — Plan de développement technique

> Version prototype pitch → production  
> Équipe : iSHEERO · Hackathon GDELT 2026

---

## 1. Architecture cible

```
┌─────────────────────────────────────────────────────────────────┐
│                         NAVIGATEUR                              │
│  Vue 3 (CDN) + Plotly.js + SVG icons inline                     │
│  ─ Landing page (sector select + chat input)                    │
│  ─ Chat stream (blocs conversation : KPIs / charts / rapports)  │
│  ─ Streaming SSE pour les rapports LLM                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────┐
│                      FASTAPI (Python)                           │
│  POST /analyze   → intent + filtrage + charts + summary         │
│  POST /report1   → SSE streaming Rapport 1 (Sonnet)             │
│  POST /report2   → SSE streaming Rapport 2 + scraping (Sonnet)  │
│  POST /followup  → SSE streaming réponse conversationnelle      │
│  POST /suggestions → 3 questions de suivi (Haiku)               │
│  GET  /health    → healthcheck                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
 ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
 │ data_service│    │  ai_service  │    │    scraper       │
 │  pandas     │    │  Anthropic   │    │  httpx + BS4     │
 │  CSV en RAM │    │  Haiku/Sonnet│    │  top 3 URLs      │
 └─────────────┘    └──────────────┘    └──────────────────┘
        │
 ┌─────────────┐
 │  GDELT CSV  │
 │  23 967 evt │
 └─────────────┘
```

---

## 2. Stack technique retenu

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| Frontend | Vue 3 CDN + Plotly.js | Zéro build step, réactif, charts pros |
| Icônes | SVG inline | Pas de dépendance CDN, contrôle total |
| Backend | FastAPI + uvicorn | Async natif, SSE facile, rapide |
| Data | Pandas en mémoire | 23k lignes = ~50ms query, pas besoin de DB |
| LLM intent | Claude Haiku 4.5 | < 0.001$ / appel, latence < 1s |
| LLM rapports | Claude Sonnet 4.6 | Qualité analytique, streaming natif |
| Scraping | httpx async + BS4 | Léger, async, timeout 8s |
| Config | python-dotenv | Séparation clé/code, `.env` gitignored |

---

## 3. Modules backend détaillés

### 3.1 `data_service.py`

**Responsabilités :**
- Chargement CSV unique au démarrage (`_df_cache` singleton)
- Enrichissement des colonnes : `root_int`, `event_code_int`, `event_root_label`, `actor1_country`, `tension_idx`
- Filtrage par secteur via combinaison de codes CAMEO :
  - `is_economic` → `EventCode ∈ ECONOMIC_CODES` (19 codes précis)
  - `is_diplomatic` → `EventCode ∈ DIPLO_CODES ∪ RootCode ∈ {4,5}`
  - `is_cooperation` → `EventRootCode ∈ {3,4,5,6,7}`
  - `is_conflict` → `EventRootCode ∈ {13..20}`
  - `is_governance` → `EventRootCode ∈ {1,2,9..12}`
- Filtrage secondaire par mots-clés sur `event_root_label`, `actor1_country`, `actor2_country`, `actor1_type`
- `summarize()` → résumé stats compact envoyé au LLM (jamais les 23k lignes brutes)
- `build_charts()` → 3 figures Plotly JSON :
  1. **Tension mensuelle** — barres colorées, anomalies en rouge, ligne de référence
  2. **Bubble Perception × Stabilité** — scatter catégories CAMEO, taille = volume, couleur = Goldstein
  3. **Signal multi-couches** — volume barres + courbe ton + courbe stabilité + bande ±1σ
- Détection anomalies : mois hors `mean ± 1.5σ` sur volume ou tension composite

**Indice de tension composite (0-100) :**
```
tension = ((-goldstein_norm × 0.6) + (-tone_norm × 0.4) + 1) / 2 × 100
goldstein_norm = GoldsteinScale.clip(-10,10) / 10
tone_norm      = AvgTone.clip(-20,20) / 20
```

### 3.2 `ai_service.py`

**Modèle Haiku** (rapide, < 0.001$/appel) :
- `extract_intent()` → JSON : `{keywords, intent_fr, data_focus}`
- `generate_suggestions()` → 3 questions de suivi contextualisées

**Modèle Sonnet** (streaming SSE) :
- `stream_report1()` → Tendances, thèmes dominants, anomalies, lecture stratégique (300-400 mots)
- `stream_report2()` → Croisement avec articles sources, explication irrégularités, angle éditorial (250-350 mots)
- `stream_followup()` → Réponse conversationnelle avec données en contexte (150-250 mots)

**Contexte système injecté (`gdelt_context.py`) :**
- Description des 20 codes CAMEO racines
- Définition précise des colonnes du dataset
- Grilles d'interprétation GoldsteinScale et AvgTone
- Mapping des secteurs et leurs codes
- Types d'acteurs (GOV, MIL, IGO, BUS, NGO...)
- Distribution réelle des données Bénin 2025

### 3.3 `scraper.py`

- Fetch async (httpx, timeout 8s, user-agent neutre)
- Extraction titre + 1500 premiers caractères de paragraphes (`<p>`)
- Déclenché sur les **3 URLs avec NumMentions le plus élevé** du slice filtré
- Silencieux en cas d'échec (l'indisponibilité d'un article ne bloque pas le pipeline)
- Résumé envoyé au LLM uniquement (pas les articles bruts complets → économie de tokens)

---

## 4. Pipeline conversationnel

```
Utilisateur (secteur + question)
         │
         ▼
  extract_intent (Haiku)
  → keywords + data_focus
         │
         ▼
  filter_data (pandas, ~10ms)
  → DataFrame filtré
         │
    ┌────┴────────────────────────────┐
    ▼                                 ▼
  summarize()                   build_charts()
  → dict stats compact           → 3 Plotly JSON
    │                                 │
    ▼                                 ▼
  /analyze retourne ──────────────────┘
  summary + charts + top_urls
         │
    ┌────┴──────────────────────────────┐
    ▼ (parallel SSE)                   ▼ (parallel SSE)
  stream_report1                  fetch_articles (async)
  (Sonnet)                        → top 3 URLs scrapées
  → Tendances + Anomalies              │
                                       ▼
                                  stream_report2 (Sonnet)
                                  → Croisement + Éditorial
         │
         ▼
  generate_suggestions (Haiku)
  → 3 questions de suivi
         │
         ▼
  Utilisateur voit : KPIs + 3 charts + 2 rapports + suggestions
         │
         ▼ (follow-up)
  stream_followup (Sonnet)
  → réponse conversationnelle avec résumé stats en contexte
```

**Latences estimées :**

| Étape | Latence |
|-------|---------|
| extract_intent (Haiku) | ~600ms |
| filter_data (pandas) | ~10ms |
| build_charts (Plotly) | ~80ms |
| /analyze total (front reçoit charts) | ~800ms |
| stream_report1 first token | ~1.2s |
| fetch_articles (3 URLs) | ~3-6s |
| stream_report2 first token | ~4-7s |
| generate_suggestions | ~500ms |
| **Perception utilisateur : premiers visuels** | **< 1s** |

---

## 5. Coût API par session

| Action | Modèle | Tokens estimés | Coût |
|--------|--------|----------------|------|
| extract_intent | Haiku | ~300 in / 150 out | ~$0.0001 |
| stream_report1 | Sonnet | ~2000 in / 600 out | ~$0.012 |
| stream_report2 | Sonnet | ~2500 in / 500 out | ~$0.014 |
| generate_suggestions | Haiku | ~400 in / 80 out | ~$0.0001 |
| follow-up × 3 | Sonnet | ~1500 in / 350 out × 3 | ~$0.024 |
| **Total session complète** | | | **~$0.05** |

> Optimisation clé : le LLM reçoit toujours le résumé stats (dict ~500 tokens), jamais le CSV brut.

---

## 6. Roadmap itérative

### Phase 0 — Prototype pitch (actuel)
- [x] Landing avec secteurs CAMEO réels
- [x] Pipeline analyze → report1 → report2 → suggestions
- [x] Streaming SSE des rapports
- [x] 3 charts Plotly informateurs (tension, bubble, signal)
- [x] Scraping top 3 URLs sources
- [x] Contexte GDELT complet injecté dans les prompts
- [x] Conversation follow-up

### Phase 1 — Stabilisation (post-pitch, ~2 jours)
- [ ] Gestion d'erreurs propre côté frontend (API down, clé invalide, données vides)
- [ ] Spinner/skeleton sur les charts pendant le chargement
- [ ] Export du rapport au format PDF (jsPDF côté client)
- [ ] Partage de session via URL (paramètres GET : `?sector=diplomatie&q=...`)
- [ ] Tests de bout en bout sur les 5 secteurs

### Phase 2 — Enrichissement données (1 semaine)
- [ ] Intégration BigQuery live (requête GDELT en temps réel, pas juste 2025)
- [ ] Filtre temporel dans l'interface (slider ou sélecteur mois)
- [ ] Carte choroplèthe des partenaires (Plotly `choropleth_mapbox`)
- [ ] Réseau d'acteurs (graphe bipartite : qui interagit avec qui, quel type d'action)
- [ ] Comparaison pays (Bénin vs pays CEDEAO sur mêmes métriques)

### Phase 3 — Expérience utilisateur avancée (2 semaines)
- [ ] Mémoire de session : l'assistant se souvient des échanges précédents dans la même session
- [ ] Profils utilisateurs (investisseur / journaliste / chercheur) → prompts différenciés
- [ ] Mode "alerte" : détection proactive d'anomalie et notification
- [ ] Annotation des charts : cliquer sur un point → explication contextuelle en pop-up
- [ ] Historique des sessions (localStorage)

### Phase 4 — Infrastructure production (1 mois)
- [ ] Déploiement sur Railway / Render (FastAPI + Gunicorn)
- [ ] Cache Redis pour les requêtes fréquentes (même secteur/même résumé)
- [ ] Rate limiting par IP (protège les coûts API)
- [ ] Auth légère (token partagé pour démo contrôlée)
- [ ] Monitoring : Sentry pour les erreurs, logging structuré des sessions
- [ ] Mise à jour automatique du CSV depuis BigQuery (cron hebdomadaire)

---

## 7. Points d'attention techniques

### Sécurité de la clé API
- `ANTHROPIC_API_KEY` dans `.env`, jamais dans le code
- `.env` dans `.gitignore` — vérifier avant chaque commit
- En production : variable d'environnement injectée par le PaaS, jamais dans le dépôt

### Gestion de la mémoire pandas
- Le DataFrame (~50MB) est chargé une seule fois via `_df_cache` global
- En production multi-worker (Gunicorn), utiliser un cache partagé (Redis) ou un worker unique pour les données

### Streaming SSE et timeouts
- Nginx en production : ajouter `proxy_read_timeout 120s` et `X-Accel-Buffering: no`
- Les rapports Sonnet peuvent prendre 15-30s pour compléter — le streaming SSE garantit une réponse progressive

### Scraping et légalité
- User-agent identifié comme bot de recherche
- Timeout 8s par article — pas de retry agressif
- Respect implicite des articles accessibles publiquement (presse internationale)
- En production : ajouter respect du `robots.txt`

---

## 8. Structure des fichiers

```
echo_media/
├── .env                    ← clé API (gitignored)
├── .env.example            ← template à committer
├── requirements.txt
├── start.ps1               ← démarrage Windows
├── SCOPE.md                ← vision produit
├── PLAN_TECHNIQUE.md       ← ce fichier
├── api/
│   ├── main.py             ← FastAPI app + routes + static
│   ├── data_service.py     ← pandas + CAMEO filtering + Plotly
│   ├── ai_service.py       ← Claude API (Haiku + Sonnet)
│   ├── scraper.py          ← httpx async article fetcher
│   ├── gdelt_context.py    ← system prompt GDELT complet
│   └── __init__.py
└── frontend/
    ├── index.html          ← Vue 3 CDN + SVG icons inline
    ├── style.css           ← design system dark
    └── app.js              ← logique Vue + SSE + Plotly render
```
