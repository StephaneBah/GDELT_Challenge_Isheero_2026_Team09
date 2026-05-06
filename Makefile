# Bénin Risk Map — Makefile cross-platform (Windows + Unix).
#
# Toutes les cibles s'appuient sur un environnement virtuel local `.venv/`
# créé automatiquement à la première utilisation. AUCUNE activation manuelle
# n'est requise — chaque cible appelle directement le binaire python du venv.
#
# Sur Windows, le binaire est .venv/Scripts/python.exe ; sur Unix, .venv/bin/python.
# La détection de l'OS se fait via la variable $(OS) (présente sous Windows).
#
# Usage habituel :
#   make install            # crée .venv + installe les deps core
#   make install-ml         # installe les deps ML lourdes (optionnel)
#   make discover-codes     # audit BigQuery (~1-2 GB scannés)
#   make extract            # extraction snapshot 12 mois
#   make process            # nettoyage + enrichissement + stories
#   make dashboard          # lance Streamlit local

# --- Détection plateforme : chemin du binaire python du venv ---
ifeq ($(OS),Windows_NT)
	PY_VENV := .venv/Scripts/python.exe
	PIP_VENV := .venv/Scripts/pip.exe
else
	PY_VENV := .venv/bin/python
	PIP_VENV := .venv/bin/pip
endif

# Python système utilisé pour créer le venv (override si besoin : `make PYTHON=py3.11 install`)
PYTHON ?= python

VENV_MARKER := .venv/pyvenv.cfg

.PHONY: help venv install install-ml discover-codes extract refresh process \
        dashboard notebook questions-list question clean-data clean-venv

help:
	@echo "Cibles disponibles :"
	@echo "  install         - cree .venv si necessaire et installe requirements.txt"
	@echo "  install-ml      - installe requirements-ml.txt (torch, transformers...)"
	@echo "  discover-codes  - audit codes CAMEO sur echantillon BigQuery"
	@echo "  extract         - extraction snapshot 12 mois (BigQuery -> Parquet)"
	@echo "  process         - clean + enrich + stories (interim -> processed)"
	@echo "  dashboard       - lance le dashboard Streamlit local"
	@echo "  notebook        - lance JupyterLab"
	@echo "  questions-list  - liste les questions du manifest"
	@echo "  question Q=Q1   - execute une question (ex: make question Q=Q1)"
	@echo "  clean-data      - supprime les fichiers intermediaires"
	@echo "  clean-venv      - supprime le venv local"

# --- Création du venv (idempotent) ---
$(VENV_MARKER):
	$(PYTHON) -m venv .venv
	$(PY_VENV) -m pip install --upgrade pip setuptools wheel

venv: $(VENV_MARKER)

# --- Installation des dépendances ---
install: $(VENV_MARKER)
	$(PY_VENV) -m pip install -r requirements.txt

install-ml: $(VENV_MARKER)
	$(PY_VENV) -m pip install -r requirements-ml.txt

# --- Pipeline ---
discover-codes:
	$(PY_VENV) -m src.pipeline.discover_codes

extract:
	$(PY_VENV) -m src.pipeline.extract

refresh:
	$(PY_VENV) -m src.pipeline.refresh

process:
	$(PY_VENV) -m src.pipeline.clean
	$(PY_VENV) -m src.pipeline.enrich
	$(PY_VENV) -m src.pipeline.stories

# --- Consommateurs ---
dashboard:
	$(PY_VENV) -m streamlit run dashboard/app.py

notebook:
	$(PY_VENV) -m jupyter lab

questions-list:
	$(PY_VENV) -m src.questions.runner --list

question:
	@if [ -z "$(Q)" ]; then echo "Usage: make question Q=Q1"; exit 1; fi
	$(PY_VENV) -m src.questions.runner --question $(Q)

# --- Nettoyage ---
clean-data:
	rm -rf data/interim/* data/processed/*
	@echo "Cleaned interim/ and processed/. raw/ preserved."

clean-venv:
	rm -rf .venv
	@echo "Venv supprime. Relancer 'make install' pour le recreer."
