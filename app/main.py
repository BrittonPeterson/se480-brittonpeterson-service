"""Table Hold: the service for openapi.yaml.

Routers implement the paths, models implement the schemas, errors.py keeps the
error model, rules.py holds the business rules, and observability.py says what
the service is doing. /health and /metrics stay unversioned and out of the
schema: they are for the platform and the operator, not for players.
"""

from fastapi import FastAPI

from app import errors, observability, store
from app.routers import reservations, tables

observability.fail_startup_if_asked()

app = FastAPI(
    title="Table Hold",
    version="1.0.0",
    summary="Find an open table in one game store and hold it for a session, without giving that table to two groups.",
    description="The hand-written contract is openapi.yaml at the repository root. This page is generated from the code and should agree with it.",
)

errors.install(app)
observability.install(app)
app.include_router(tables.router)
app.include_router(reservations.router)


@app.get("/health", tags=["Operational"], summary="Health check", include_in_schema=False)
def health():
    # Counts, never contents. A restart shows here: started_at moves and the
    # reservation counts fall to zero.
    holds = list(store.RESERVATIONS.values())
    return observability.health_report(
        {
            "tables": len(store.TABLES),
            "reservations": len(holds),
            "confirmed": sum(1 for hold in holds if hold.status == "confirmed"),
        }
    )


@app.get("/metrics", tags=["Operational"], summary="Metrics", include_in_schema=False)
def metrics():
    return observability.metrics_response()
