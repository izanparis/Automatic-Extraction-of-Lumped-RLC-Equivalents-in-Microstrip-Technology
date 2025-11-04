
.PHONY: setup lint fix test run

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && \
	pip install -e . && pip install ruff black pytest

lint:
	ruff check src && black --check src

fix:
	black src && ruff check src --fix

test:
	pytest -q

run:
	python -m tfg_v0.cli fit data/raw/ejemplo.s2p --cfg config/base.yaml --out reports
