# Echo Média

Expérience conversationnelle sur les données médiatiques GDELT du Bénin 2025.

## Prérequis

- Python 3.11+
- Clé API Anthropic → [console.anthropic.com](https://console.anthropic.com)

## Installation

```powershell
cd echo_media
pip install -r requirements.txt
```

## Configuration
Créer un fichier .env
```powershell
# La clé est déjà dans .env — vérifier qu'elle est valide
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

Ouvrir **http://localhost:8000**

## Mode démo

Si la clé API est absente ou invalide, le serveur démarre automatiquement en mode démo — vrais charts depuis le CSV, rapports pré-rédigés.


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
