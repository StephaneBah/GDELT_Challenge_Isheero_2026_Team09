# Hackathon iSHEERO X Datacamp 2026 — Bénin Insights Challenge

## Vision
Notre analyse explore la position du Bénin sur l'échiquier international à travers **GDELT 2025**.

1. **Le Bénin vu d'ailleurs (couverture médiatique & perception)**
   - Traitement médiatique international, tonalité et signaux de stabilité.
   - Lecture de la perception globale et des narratifs dominants.

2. **Diplomatie et attractivité économique**
   - Cartographie des partenariats et acteurs dominants.
   - Impact des accords et interactions sur la stabilité perçue.

## Livrables principaux
- **Echo Media** : expérience conversationnelle qui filtre GDELT par secteur/période et génère visuels + rapports IA.
- **Dashboard Streamlit** : exploration analytique avancée (filtres, anomalies, sources, clustering).
- **Notebooks & scripts** : collecte, nettoyage, et analyses exploratoires.

## Démarrage rapide (Echo Media)
```powershell
cd echo_media
pip install -r requirements.txt
cd api
uvicorn main:app --reload --port 8000
```
Puis ouvrir http://localhost:8000

## Structure du dépôt
```
echo_media/   # app conversationnelle (FastAPI + frontend)
dashboard/    # dashboard Streamlit (app.py, v2, v3)
data/         # jeux de données GDELT et CAMEO
notebooks/    # notebooks d'analyse
```
