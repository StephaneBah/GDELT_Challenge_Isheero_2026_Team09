.PHONY: install install-ml run clean

install:
	python -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

install-ml:
	.venv/bin/pip install -r requirements-ml.txt

run:
	.venv/bin/streamlit run dashboard/app.py

clean:
	rm -rf .venv __pycache__ .pytest_cache
