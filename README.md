# se480-brittonpeterson-service

Deployed at: https://se480-brittonpeterson-service.onrender.com

## Run it
Open this repository in a Codespace (Code → Codespaces → Create codespace on main). The dev container installs `requirements.txt` before the terminal is ready. Then:

    python -m uvicorn app.main:app --reload --port 8000

Open the forwarded port 8000. `GET /health` returns `"status": "ok"` plus the fields described under "Operate it". The Table Hold API is under `/v1` (for example `GET /v1/tables`). Generated docs are at `/docs`. Leave the port private to your GitHub account.

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

`make lint` and `make mock` run those same two commands.

## Test it

    make test

That is `python -m pytest -q`: the smoke test, unit tests for every operation and error, direct tests of `app/rules.py`, the 500 handler test, the contract tests (Schemathesis against `openapi.yaml`, plus the drift check that the code and the spec declare the same operations), the Lab 5 logging, health, and metrics tests in `tests/test_observability.py`, and `tests/test_concurrency.py`. The last one is expected to fail and is reported as `1 xfailed`. See Known limits.

The first contract run in Lab 3 accepted a create body that set `player_count` to null. The spec does not allow null for that field, only omitting it, so the models now reject an explicit null. The same rule applies to the other optional fields.

## Check it

    make check

It runs three checks and stops at the first one that fails:

- `make lint-py` runs `ruff check .` and `ruff format --check .`. Clean means "All checks passed!" and "files already formatted". There are no ignores, in the config or on any line.
- `make coverage` runs the tests with a coverage map. Clean means every test passes and the total is at or above the `fail_under = 85` floor in `pyproject.toml`. It is 100% today, and `app/rules.py` is at 100%.
- `make audit` runs `pip-audit -r requirements.txt` against the pinned versions. Clean means "No known vulnerabilities found".

CI runs the same three steps on every push. Dependencies are declared with ranges in `requirements.in` and pinned by `make pin` into `requirements.txt`, which is what CI, Render, and a Codespace install. Dependabot proposes upgrades weekly.

What the first run found before it was fixed: ruff wanted 9 files reformatted and reported 7 findings (`Query(...)` calls in argument defaults, `timezone.utc` instead of `datetime.UTC`, and an unsorted import block). Coverage was 97% overall but `app/rules.py` was at 91%: the under-an-hour, more-than-14-days, closed-day, outside-open-hours, and cancelled-patch rules had never been reached by a test. The audit was clean. The `Query` findings were fixed with FastAPI's `Annotated[..., Query(...)]` form, and the rules each got a test whose docstring names the line it covers.

Two notes for anyone redoing this from the course template. Its `requirements.in` asks for `httpx2>=0.28,<1`, but httpx2 releases start at 2.0, so `make pin` cannot resolve it; this repo uses `httpx2>=2,<3`. And ruff 0.17, which the template's `ruff>=0.8,<1` range allows, enables more rules by default than the template's comment lists (bugbear, pyupgrade, and import sorting among them). They were fixed here rather than turned off.

## Mock it

    npx -y @stoplight/prism-cli mock openapi.yaml --port 4010

In a second terminal, with no `/v1` in the path:

    curl -i http://127.0.0.1:4010/tables

To see a problem-details body, add `-H "Prefer: code=404"` on a path that documents 404, such as `/tables/tbl_7f3k9q2d`.

## Change applied
Review received: "Your service works fine, but looks to follow the example exactly. I would add an additional operation or a new kind of error that diverges it from the working example."

Change: a new operation, `GET /v1/tables/{table_id}/openings?date=YYYY-MM-DD`, that the course example does not have. It returns the free stretches on one day: the table's open hours with confirmed holds cut out, earliest first, in the table's time zone. Today's stretches start at the next quarter hour, and `min_length_minutes` (60 to 360) leaves out gaps too short to book. A player can ask "when is Table 4 free on Tuesday?" in one call instead of listing reservations and working out the gaps. It is in `openapi.yaml`, the design sheet, `app/routers/tables.py`, and `tests/test_openings.py`, and the contract and drift tests cover it. Holds that start in the past are also now rejected with 400.

While implementing, explicit null on an optional field was rejected in the code rather than allowed in the spec, because the spec already says those fields are integers or strings and not null.

Rules the spec gained in Lab 4: `ReservationCreate`, `ReservationPatch`, and `Requester` now say `additionalProperties: false`. The code already rejected unknown fields on create and patch, but the spec did not say so, and `requester` silently dropped them (`{"is_admin": true}` was accepted and thrown away). All three now return 400 naming the field. The list window's `window_start` and `window_end` are parsed as offset-aware date-times, so a missing offset is rejected by the model rather than by a check in the router. The rules that were still written in the routers (both window bounds or neither, the openings date range, seats, and the cancelled-patch rule) moved into `app/rules.py` so each rule lives in one place.

## Operate it

**Logs.** On Render: the service's Logs page. Locally: the terminal running uvicorn. Every request writes one JSON line with the fields `ts`, `level`, `request_id`, `method`, `route`, `status`, and `duration_ms`. `route` is the route template, like `/v1/reservations/{reservation_id}`, never the real path, so reservation ids, names, and emails never reach the log. A path that matches no route is logged as `"unmatched"`. A 5xx is logged at `ERROR`, and the 500 handler also logs the traceback with the request id and route. uvicorn's own access log is turned off (`--no-access-log` in the `Dockerfile` and `make run`), because it would log the real path and a second line per request.

Three lines from Render's log, found on the Logs page by searching for their request ids. These are the double-booking run in [docs/postmortem.md](docs/postmortem.md): a refused duplicate, then the two creates that were both accepted, 1 ms apart.

    {"ts":"2026-11-23T18:35:18.131Z","level":"INFO","request_id":"d8a291d3e17ef4c5","method":"POST","route":"/v1/tables/{table_id}/reservations","status":409,"duration_ms":1.38}
    {"ts":"2026-11-23T18:35:19.353Z","level":"INFO","request_id":"13cff083a76a3600","method":"POST","route":"/v1/tables/{table_id}/reservations","status":201,"duration_ms":2.25}
    {"ts":"2026-11-23T18:35:19.354Z","level":"INFO","request_id":"8632340d2df162c0","method":"POST","route":"/v1/tables/{table_id}/reservations","status":201,"duration_ms":3.05}

**Request ids.** Every response carries `X-Request-ID`. A caller can send its own `X-Request-ID`, which is kept if it is 8 to 64 letters, digits, `.`, `_` or `-`. Anything else is replaced with a new id. A 500's body asks the caller to report the id, and the id finds the matching log line.

**Health.** `GET /health` on the deployed service, right after the SLO run:

    {"status":"ok","started_at":"2026-11-23T18:34:01Z","uptime_seconds":65,"commit":"cca76c6","store":{"tables":2,"reservations":60,"confirmed":0}}

`commit` is Render's `RENDER_GIT_COMMIT`, shortened, and is `"unknown"` locally. `reservations` counts every hold in memory, including cancelled ones, and `confirmed` counts the ones still held. Render's Health Check Path is `/health`. Render calls it every few seconds, so `/health` and `/metrics` are neither logged nor counted. Otherwise they would drown out the journey in both. The service's notifications use the workspace default, "Only failure notifications".

**Metrics.** `GET /metrics` is in Prometheus text format:

- `http_requests_total{route, status}`, where `status` is the class (`2xx`, `4xx`, `5xx`)
- `http_request_duration_seconds{route}`, a histogram with buckets from 0.05 s to 5 s
- `table_conflicts_total`, holds refused with 409 because the table was already held

Counters live in the process and start from zero on every restart.

**What the log answered.** On a local run of ten hand-picked requests plus the SLO load, the log alone showed the following. The slowest request was the first create after startup, at 8.39 ms, while every other request took under 1 ms. 21 requests ended in a 4xx. The request sent with `X-Request-ID: britton-kept-0001` kept that id and was a create on `/v1/tables/{table_id}/reservations` that returned 201. The first version logged `duration_ms` in whole milliseconds, so nearly every line read 0 or 1 and "slowest" had no answer. It now has two decimals.

**SLO.** 99% of journey requests not a 5xx and under one second, over 7 days. Measured once against Render, both were 315 / 315. See [docs/slo.md](docs/slo.md).

**Breaking it on purpose.** Platform: setting `LAB5_FAIL_STARTUP=1` in Render's environment makes the app exit before it starts. It was set on Mon Nov 23, 2026 at 1:56 PM CST with "Save, rebuild, and deploy". The image built from cache in about 2 seconds. The deploy log then showed `LAB5_FAIL_STARTUP=1: refusing to start, on purpose (Lab 5, task 6).` at 1:56:34 PM, followed by `==> Exited with status 1` at 1:56:36. Render restarted the instance at 1:56:37, and it refused again. The Events page recorded "Deploy failed for 201557a", and the notice said "Exited with status 1 while running your code." The old instance kept serving throughout: `/health`, polled every 15 seconds from 1:56 to 2:01 PM, answered `ok` with commit `201557a` every time. Its `started_at` changed once, to 19:56:51Z, during the failed deploy. The dashboard doesn't say why. Deleting the variable started a new deploy at 1:59 PM, which went live the same minute (`started_at` 19:59:34Z). TODO: the failure email's subject line and arrival time. The failure that matters: [docs/postmortem.md](docs/postmortem.md).

**Milestone 2:** [docs/milestone2.md](docs/milestone2.md).

## Known limits
- **Double booking under concurrent requests.** The overlap check reads the store and then writes to it with no lock, so two near-simultaneous creates for the same window can both return 201. This is the failure the design sheet names. It happened in 1 of 20 simultaneous pairs against Render, reproduced by [`scripts/double_hold.py`](scripts/double_hold.py). [`tests/test_concurrency.py`](tests/test_concurrency.py) reproduces it every time as an expected failure. Written up in [docs/postmortem.md](docs/postmortem.md). The fix is the Week 6 store decision and the final.
- **The store is in memory.** Every reservation is lost when Render restarts the instance, which on the free plan happens after about fifteen idle minutes. That is also Week 6.
- **`/metrics` is public, and its counters reset on restart.** It shows only counts by route template, with no ids or names. A restart, including Render's sleep, starts every count from zero, so a window longer than the current process can't be measured from it.
- **No login.** Anyone with a reservation id can cancel it.
- **Audit findings:** none stand. `pip-audit` reports no known vulnerabilities in the pinned versions.
- **Coverage floor:** still 85, not lowered.

## What's here
- `app/` — the Table Hold FastAPI service (`/v1` plus `GET /health` and `GET /metrics`). `app/observability.py` holds the request ids, log lines, counters, and health report.
- `tests/` — smoke, unit, rules, error-handler, contract, observability, and concurrency tests
- `scripts/double_hold.py` — races pairs of identical holds against a running service and reports any that were both accepted
- `scripts/slo_load.py` — sends load along the journey and computes the SLI from `/metrics`
- `docs/slo.md`, `docs/postmortem.md`, `docs/milestone2.md` — the Lab 5 SLO, the double-booking postmortem, and the Milestone 2 status page
- `client/example.py` — a small client that lists tables, shows a day's openings, holds one, and shows a conflict in sentences
- `docs/proposal.md` — the Milestone 1 proposal
- `openapi.yaml` — the Table Hold API spec
- `design-sheet.md` — the seven-line sheet the spec was written from
- `schemathesis.toml` — tells the contract test that 400 is a valid answer for a rule the schema cannot express
- `.spectral.yaml` — Spectral rules for the spec
- `Makefile` — `test`, `lint`, `mock`, and `client`, plus the Lab 4 targets `lint-py`, `format`, `coverage`, `audit`, `pin`, and `check`
- `requirements.in` — the dependencies a person edits, with ranges; `requirements.txt` — the same, pinned by `make pin`
- `pyproject.toml` — pytest, ruff, and coverage settings, including the coverage floor
- `.github/dependabot.yml` — weekly upgrade pull requests for pip and GitHub Actions
- `.devcontainer/` — the Codespace environment (Python 3.12 and Node, installs Python dependencies on create)
- `Dockerfile` — the image Render builds
- `scripts/smoke.sh` — curls a deployed `/health`
- `.github/workflows/ci.yml` — on every push and pull request, installs the pinned dependencies, then runs ruff, the tests with the coverage floor, and pip-audit; if the `APP_URL` repository variable is set, a second job curls that deployed `/health`

## Help received
none

## AI tools used
Lab 1: Cursor helped a little. Most of the work was done by me.
Lab 2: Cursor drafted `openapi.yaml`, `.spectral.yaml`, the Makefile, `design-sheet.md`, and the Lab 2 sections of this README from the Table Hold design I chose. I am responsible for every line of the spec.
Lab 3: Cursor drafted the service (`app/models.py`, `app/errors.py`, `app/rules.py`, `app/store.py`, the routers), the unit and contract tests, `client/example.py`, `schemathesis.toml`, `docs/proposal.md`, and the Lab 3 README sections, following the course reference shape and this spec. After the review, Cursor also drafted the openings operation and the past-hold rule, with their spec text and tests. I am responsible for every line.
Lab 4: Cursor copied in the template toolchain (`requirements.in`, the pinned `requirements.txt`, the `pyproject.toml` blocks, the Makefile targets, the CI steps, `.github/dependabot.yml`) and wrote the last-resort 500 handler in `app/errors.py`. It also moved the remaining rules from the routers into `app/rules.py`, fixed the ruff findings, added `additionalProperties: false` to the spec, and wrote the new tests: `tests/test_rules.py`, `tests/test_errors.py`, and the new cases in `tests/test_reservations.py`. It drafted the Lab 4 README sections. I am responsible for every line.
Lab 5: Cursor wrote `app/observability.py` (following the course reference shape), the `/health` and `/metrics` changes, the conflict counter, `tests/test_observability.py`, `tests/test_concurrency.py`, both scripts in `scripts/`, and drafts of `docs/slo.md`, `docs/postmortem.md`, `docs/milestone2.md`, and the Lab 5 README sections. It also ran the measurements quoted in them. I am responsible for every line.
