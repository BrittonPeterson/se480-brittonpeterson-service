# se480-brittonpeterson-service

Deployed at: https://se480-brittonpeterson-service.onrender.com

## Run it
Open this repository in a Codespace (Code → Codespaces → Create codespace on main). The dev container installs `requirements.txt` before the terminal is ready. Then:

    python -m uvicorn app.main:app --reload --port 8000

Open the forwarded port 8000. `GET /` returns the greeting, and `GET /health` returns `{"status":"ok"}`. Leave the port private to your GitHub account.

Outside a Codespace, install dependencies first, then use the same command:

    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000

## Test it

    python -m pytest -q

Lint the API spec, then start the mock:

    npx -y @stoplight/spectral-cli lint openapi.yaml
    npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

`make lint` and `make mock` run those same two commands.

## Mock it

    npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

In a second terminal, with no `/v1` in the path:

    curl -i http://127.0.0.1:4010/tables

To see a problem-details body, add `-H "Prefer: code=404"` on a path that documents 404, such as `/tables/tbl_7f3k9q2d`.

## Change applied
No classmate review has been posted yet, so no review change is applied.

## What's here
- `app/` — the FastAPI service (`GET /` and `GET /health`)
- `tests/` — the smoke test for `/health`
- `openapi.yaml` — the Table Hold API spec
- `design-sheet.md` — the seven-line sheet the spec was written from
- `.spectral.yaml` — Spectral rules for the spec
- `Makefile` — `lint` and `mock` targets
- `.devcontainer/` — the Codespace environment (Python 3.12 and Node, installs Python dependencies on create)
- `Dockerfile` — the image Render builds
- `scripts/smoke.sh` — curls a deployed `/health`
- `.github/workflows/ci.yml` — on every push and pull request, installs dependencies and runs the smoke test; if the `APP_URL` repository variable is set, a second job curls that deployed `/health`

## Help received
none

## AI tools used
Lab 1: Cursor helped a little. Most of the work was done by me.
Lab 2: Cursor drafted `openapi.yaml`, `.spectral.yaml`, the Makefile, `design-sheet.md`, and the Lab 2 sections of this README from the Table Hold design I chose. I am responsible for every line of the spec.
