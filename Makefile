# ========== Makefile ==========
#
# Utilisation :
#   make install      -> crée le venv + installe requirements.txt
#   make install-ml   -> installe les dépendances ML
#   make run          -> lance l'application Streamlit
#   make clean        -> supprime les fichiers temporaires
#
# Exemple :
#   make setup
#	make run 
# ========================================

.PHONY: setup install install-ml run clean

setup: install install-ml

install:
	python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

install-ml:
	.venv/bin/pip install -r requirements-ml.txt

run:
	.venv/bin/streamlit run dashboard/app.py

clean:
	rm -rf .venv __pycache__ .pytest_cache

