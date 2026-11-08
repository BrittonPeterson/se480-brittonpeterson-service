.PHONY: run test lint mock client

run:
	python -m uvicorn app.main:app --reload --port 8000

test:
	python -m pytest -q

lint:
	npx -y @stoplight/spectral-cli lint openapi.yaml

mock:
	npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

client:
	python client/example.py $(APP_URL) 
