.PHONY: run test lint mock client lint-py format coverage audit pin check

run:
	python -m uvicorn app.main:app --reload --port 8000 --no-access-log

test:
	python -m pytest -q

lint:
	npx -y @stoplight/spectral-cli lint openapi.yaml

mock:
	npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

client:
	python client/example.py $(APP_URL)

# Lab 4: the three checks, and the one command that runs them all.

lint-py:
	ruff check . && ruff format --check .

format:
	ruff format . && ruff check --fix .

coverage:
	python -m pytest -q --cov=app --cov-report=term-missing

audit:
	pip-audit -r requirements.txt

pin:
	pip-compile --quiet --output-file=requirements.txt requirements.in

check: lint-py coverage audit
