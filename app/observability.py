"""Lab 5: what the service says about itself while it runs.

One middleware does three things for every request: gives it an id, counts it,
and writes one JSON line when the response is sent. Nothing in this module
knows what Table Hold is for; the counter that belongs to a business rule
lives beside that rule, in the reservations router.
"""

import json
import os
import re
import secrets
import sys
import time
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUEST_ID_HEADER = "X-Request-ID"

# A request that matches no route gets this label, never the raw path. Table
# Hold has no login, so a reservation id in a path is the only key to that
# hold: anyone who reads it can cancel the reservation.
UNMATCHED = "unmatched"

# Render polls /health every few seconds, and /metrics is read by whoever is
# watching. Neither is a player, so neither is logged or counted: they would
# drown the log and flatter the SLI.
QUIET_PATHS = frozenset({"/health", "/metrics"})

# An incoming X-Request-ID is kept only if it looks like an id. Anything else is
# replaced, because the value goes straight into the log.
_ACCEPTABLE_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")

STARTED_AT = datetime.now(UTC)

REQUESTS = Counter(
    "http_requests_total",
    "Requests handled, by route template and status class.",
    ["route", "status"],
)
DURATION = Histogram(
    "http_request_duration_seconds",
    "Seconds from request received to response sent, by route template.",
    ["route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def fail_startup_if_asked() -> None:
    """Lab 5, task 6: a break the platform can see.

    Set LAB5_FAIL_STARTUP=1 in the service's environment on Render and the next
    deploy refuses to start; delete the variable to repair it. Only the
    service's owner can set it, and it is read once, at startup.
    """
    if os.environ.get("LAB5_FAIL_STARTUP") == "1":
        raise SystemExit("LAB5_FAIL_STARTUP=1: refusing to start, on purpose (Lab 5, task 6).")


def request_id(request: Request) -> str:
    """The id this request was given, or "-" if the middleware never saw it."""
    return getattr(request.state, "request_id", "-")


def route_template(request: Request) -> str:
    """The matched route as the code wrote it, e.g. /v1/reservations/{reservation_id}."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or UNMATCHED


def log_line(**fields) -> None:
    """One JSON object on one line of standard output, where Render's log view collects it."""
    now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    sys.stdout.write(json.dumps({"ts": now, **fields}, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _record(request: Request, status: int, started: float) -> None:
    elapsed = time.perf_counter() - started
    route = route_template(request)
    REQUESTS.labels(route=route, status=f"{status // 100}xx").inc()
    DURATION.labels(route=route).observe(elapsed)
    log_line(
        level="ERROR" if status >= 500 else "INFO",
        request_id=request_id(request),
        method=request.method,
        route=route,
        status=status,
        # Two decimals: whole milliseconds logged nearly every request as 0 or 1,
        # so "which was slowest" could not be answered from the log.
        duration_ms=round(elapsed * 1000, 2),
    )


async def observe(request: Request, call_next) -> Response:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    request.state.request_id = (
        incoming if _ACCEPTABLE_ID.fullmatch(incoming) else secrets.token_hex(8)
    )
    quiet = request.url.path in QUIET_PATHS
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # The last-resort handler in errors.py runs outside this middleware, so
        # its 500 never comes back through here. Record the request now and let
        # the exception carry on to that handler, which sets the header itself.
        if not quiet:
            _record(request, 500, started)
        raise
    response.headers[REQUEST_ID_HEADER] = request.state.request_id
    if not quiet:
        _record(request, response.status_code, started)
    return response


def health_report(store: dict[str, int]) -> dict:
    """What /health returns: still cheap, still 200, and now it says something.

    `store` is counts and never contents: how many holds, not whose.
    """
    uptime = datetime.now(UTC) - STARTED_AT
    return {
        "status": "ok",
        "started_at": STARTED_AT.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "uptime_seconds": int(uptime.total_seconds()),
        "commit": os.environ.get("RENDER_GIT_COMMIT", "")[:7] or "unknown",
        "store": store,
    }


def metrics_response() -> Response:
    """The Prometheus text format, for a /metrics route kept out of the schema."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def install(app: FastAPI) -> None:
    app.middleware("http")(observe)
