# SLO: Table Hold

## The promise, in one sentence

Over any 7 days, 99% of requests along the find-and-hold journey get an answer that is not a 5xx, in under one second, measured from the service's own `/metrics`, not counting the time Render spends waking a sleeping instance.

## The parts

- **User journey it protects:** a player looks for a free table tonight and holds it, then checks or cancels the hold. Four routes carry it: `GET /v1/tables`, `GET /v1/tables/{table_id}/openings`, `GET` and `POST /v1/tables/{table_id}/reservations`, and `GET`, `PATCH` and `DELETE /v1/reservations/{reservation_id}`.
- **SLI (good events over valid events):** valid is every request to those four route templates. Good is a valid request answered with a status below 500, in under one second. A 409 for a taken window and a 400 for a hold in the past are good: the service did its job and said no. The two conditions are counted by different metrics, so the SLI is two fractions, and the promise holds only when both do.
- **Where it is measured:** `/metrics`, for the four routes. Not a 5xx: `http_requests_total` with status `2xx` or `4xx`, over `http_requests_total` with any status. Under one second: `http_request_duration_seconds_bucket{le="1.0"}` over `http_request_duration_seconds_count`. `scripts/slo_load.py` reads both and does the division.
- **Target and window:** 99% for each fraction, over any 7 days.
- **Excluded, and why:** Render's wake-up. The free instance sleeps after about 15 idle minutes and takes around 30 seconds to wake. Render holds the request while the process starts, and the service's clock only starts when the request reaches the app, so that wait never shows up in the histogram. The exclusion is free to implement, but it also means the SLI cannot see the delay a player notices most. `/health`, `/metrics`, and paths that match no route (`route="unmatched"`) are outside the journey and are not valid events.

## Measured once

- **When, and against what:** Monday Nov 23, 2026, against https://se480-brittonpeterson-service.onrender.com. `/health` reported `started_at` 2026-11-23T18:34:01Z and commit `cca76c6`.
- **The window I actually had:** since `started_at`, about one minute, not seven days. The counters live in the process and reset on every restart, and the free instance restarts whenever it sleeps, so a 7-day window can't be measured from `/metrics` alone.
- **Requests sent:** 315, from `python scripts/slo_load.py https://se480-brittonpeterson-service.onrender.com 60`. Each of 60 rounds lists tables, asks for a day's openings, creates a hold, lists the table's holds, and cancels the hold. Every 4th round also sends a duplicate create that is refused with 409.
- **The arithmetic:** not a 5xx: 315 / 315 = 100.00%. Under one second: 315 / 315 = 100.00%. The slowest bucket used was the first one: all 135 requests on `/v1/tables/{table_id}/reservations` landed under 0.05 s, with a summed duration of 0.198 s, about 1.5 ms each.
- **Log cross-check, on a local run:** the same load (plus ten hand-picked requests) ran against `uvicorn` on port 8000, with the log written to a file. The log had 323 lines on the four journey routes: 304 were 2xx, 19 were 4xx, none were 5xx, and all 323 had `duration_ms` under 1000. `/metrics` on the same process gave 323 for each of the same counts: 61 + 2 on `/v1/tables`, 61 on openings, 121 + 16 on the table's reservations, and 61 + 1 on a single reservation. They agree, and they should, because one function in `app/observability.py` writes the log line and moves the counters for the same request. All 323 request ids in the log were distinct.

## When the budget is spent

New features stop until the 5xx or slow answers are explained in writing. For Table Hold that moves the Week 6 store and lock decision ahead of everything else, because a slower, durable store is the change most likely to spend it.
