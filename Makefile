# Bénin Risk Map — commandes courantes
# Usage : `make <target>`. Sur Windows sans `make`, voir le README.

.PHONY: help install discover-codes extract refresh clean-data process dashboard notebook question questions-list test

help:
	@echo "Cibles disponibles :"
	@echo "  install         — installe les dépendances Python"
	@echo "  discover-codes  — audit des codes CAMEO sur échantillon BigQuery (à lancer avant extract)"
	@echo "  extract         — extraction one-shot 12 mois (BigQuery -> Parquet)"
	@echo "  refresh         — refresh incrémental (events du jour)"
	@echo "  process         — interim -> processed (agrégats prêts pour viz/ML)"
	@echo "  dashboard       — lance le dashboard Streamlit local"
	@echo "  notebook        — lance JupyterLab"
	@echo "  questions-list  — liste les questions du manifest"
	@echo "  question Q=Q1   — exécute une question (ex: make question Q=Q1)"
	@echo "  clean-data      — supprime les fichiers intermédiaires (garde raw)"

install:
	pip install -r requirements.txt

discover-codes:
	python -m src.pipeline.discover_codes

extract:
	python -m src.pipeline.extract

refresh:
	python -m src.pipeline.refresh

process:
	python -m src.pipeline.clean
	python -m src.pipeline.enrich
	python -m src.pipeline.stories

dashboard:
	streamlit run dashboard/app.py

notebook:
	jupyter lab

questions-list:
	python -m src.questions.runner --list

question:
	@if [ -z "$(Q)" ]; then echo "Usage: make question Q=Q1"; exit 1; fi
	python -m src.questions.runner --question $(Q)

clean-data:
	rm -rf data/interim/* data/processed/*
	@echo "Cleaned interim/ and processed/. raw/ preserved."
