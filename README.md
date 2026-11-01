# se480-brittonpeterson-service

Deployed at: not deployed yet. After the Render deploy, replace this line with the public `https://` URL and no trailing slash.

## Run it
Open this repository in a Codespace (Code → Codespaces → Create codespace on main). The dev container installs `requirements.txt` before the terminal is ready. Then:

    python -m uvicorn app.main:app --reload --port 8000

Open the forwarded port 8000. `GET /` returns the greeting, and `GET /health` returns `{"status":"ok"}`. Leave the port private to your GitHub account.

Outside a Codespace, install dependencies first, then use the same command:

    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000

## Test it

    python -m pytest -q

## What's here
- `app/` — the FastAPI service (`GET /` and `GET /health`)
- `tests/` — the smoke test for `/health`
- `.devcontainer/` — the Codespace environment (Python 3.12, installs dependencies on create)
- `Dockerfile` — the image Render builds
- `scripts/smoke.sh` — curls a deployed `/health`
- `.github/workflows/ci.yml` — on every push and pull request, installs dependencies and runs the smoke test; if the `APP_URL` repository variable is set, a second job curls that deployed `/health`

## Help received
none

## AI tools used
Cursor helped a little. Most of the work was done by me.
