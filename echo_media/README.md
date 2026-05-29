# Echo Média

Expérience conversationnelle sur les données médiatiques GDELT du Bénin 2025.

## Ce que fait la démo
- Comprend l'intention, le secteur et la période demandée.
- Filtre le slice GDELT correspondant (pandas en mémoire).
- Génère des visuels pertinents selon la question et les données filtrées.
- **Rapport 1** : tendances & anomalies.
- **Rapport 2** : mini‑reportage basé sur articles GDELT + recherche web.
- Suggestions de questions et follow‑up conversationnel.

## Prérequis
- Python 3.11+
- Clé API Anthropic → https://console.anthropic.com

## Installation
```powershell
cd echo_media
pip install -r requirements.txt
```

## Configuration
Créer un fichier .env
```powershell
# ANTHROPIC_API_KEY=sk-ant-...
# DATA_PATH=../data/GDELT_events_benin_2025_cleaned.csv
```

## Lancement
```powershell
cd echo_media\api
uvicorn main:app --reload --port 8000

ou

.\start.ps1
```

Ouvrir http://localhost:8000

## Endpoints clés
- POST /analyze
- POST /report1
- POST /report2
- POST /followup
- POST /suggestions
- POST /route
- GET /health

## Mode démo
Si la clé API est absente ou invalide, le serveur démarre en mode démo.

## Structure
```
echo_media/
├── api/
│   ├── main.py           # FastAPI — routes
│   ├── data_service.py   # Filtrage pandas + charts Plotly
│   ├── ai_service.py     # Claude Haiku + Sonnet
│   ├── scraper.py        # Lecture articles sources
│   └── gdelt_context.py  # Contexte GDELT injecté dans les prompts
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```
