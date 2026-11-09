# se480-brittonpeterson-service

Deployed at: https://se480-brittonpeterson-service.onrender.com

## Run it
Open this repository in a Codespace (Code → Codespaces → Create codespace on main). The dev container installs `requirements.txt` before the terminal is ready. Then:

    python -m uvicorn app.main:app --reload --port 8000

Open the forwarded port 8000. `GET /health` returns `{"status":"ok"}`. The Table Hold API is under `/v1` (for example `GET /v1/tables`). Generated docs are at `/docs`. Leave the port private to your GitHub account.

Outside a Codespace, install dependencies first, then use the same command:

    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000

Run the sample client against a local server, or against Render. A sleeping Render service takes about 30 seconds to wake; the client waits up to 60 seconds and says so.

    python client/example.py http://127.0.0.1:8000
    python client/example.py https://se480-brittonpeterson-service.onrender.com

`GET /tables` was checked for read-aloud text. The summary, each filter's description, and the 400 problem-details response are on the page. No wording was changed.

Lint the API spec, then start the mock:

    npx -y @stoplight/spectral-cli lint openapi.yaml
    npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

`make lint` and `make mock` run those same two commands. `make test` runs the unit tests and the contract tests.

## Test it

    python -m pytest -q

The first contract run accepted a create body that set `player_count` to null. The spec does not allow null for that field, only omitting it, so the models now reject an explicit null. The same rule applies to the other optional fields.

## Mock it

    npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

In a second terminal, with no `/v1` in the path:

    curl -i http://127.0.0.1:4010/tables

To see a problem-details body, add `-H "Prefer: code=404"` on a path that documents 404, such as `/tables/tbl_7f3k9q2d`.

## Change applied
Review received: "Your service works fine, but looks to follow the example exactly. I would add an additional operation or a new kind of error that diverges it from the working example."

Change: a new operation, `GET /v1/tables/{table_id}/openings?date=YYYY-MM-DD`, that the course example does not have. It returns the free stretches on one day: the table's open hours with confirmed holds cut out, earliest first, in the table's time zone. Today's stretches start at the next quarter hour, and `min_length_minutes` (60 to 360) leaves out gaps too short to book. A player can ask "when is Table 4 free on Tuesday?" in one call instead of listing reservations and working out the gaps. It is in `openapi.yaml`, the design sheet, `app/routers/tables.py`, and `tests/test_openings.py`, and the contract and drift tests cover it. Holds that start in the past are also now rejected with 400.

While implementing, explicit null on an optional field was rejected in the code rather than allowed in the spec, because the spec already says those fields are integers or strings and not null.

## What's here
- `app/` — the Table Hold FastAPI service (`/v1` plus `GET /health`)
- `tests/` — smoke, unit, and contract tests
- `client/example.py` — a small client that lists tables, shows a day's openings, holds one, and shows a conflict in sentences
- `docs/proposal.md` — the Milestone 1 proposal
- `openapi.yaml` — the Table Hold API spec
- `design-sheet.md` — the seven-line sheet the spec was written from
- `schemathesis.toml` — tells the contract test that 400 is a valid answer for a rule the schema cannot express
- `.spectral.yaml` — Spectral rules for the spec
- `Makefile` — `test`, `lint`, `mock`, and `client` targets
- `.devcontainer/` — the Codespace environment (Python 3.12 and Node, installs Python dependencies on create)
- `Dockerfile` — the image Render builds
- `scripts/smoke.sh` — curls a deployed `/health`
- `.github/workflows/ci.yml` — on every push and pull request, installs dependencies and runs the tests; if the `APP_URL` repository variable is set, a second job curls that deployed `/health`

## Help received
none

## AI tools used
Lab 1: Cursor helped a little. Most of the work was done by me.
Lab 2: Cursor drafted `openapi.yaml`, `.spectral.yaml`, the Makefile, `design-sheet.md`, and the Lab 2 sections of this README from the Table Hold design I chose. I am responsible for every line of the spec.
Lab 3: Cursor drafted the service (`app/models.py`, `app/errors.py`, `app/rules.py`, `app/store.py`, the routers), the unit and contract tests, `client/example.py`, `schemathesis.toml`, `docs/proposal.md`, and the Lab 3 README sections, following the course reference shape and this spec. After the review, Cursor also drafted the openings operation and the past-hold rule, with their spec text and tests. I am responsible for every line.
