"""Table Hold: the Lab 3 service for openapi.yaml.

Routers implement the paths, models implement the schemas, errors.py keeps the
error model, and rules.py holds the business rules. /health stays unversioned
so Render and the CI smoke test can call it.
"""

from fastapi import FastAPI

from app import errors
from app.routers import reservations, tables

app = FastAPI(
    title="Table Hold",
    version="1.0.0",
    summary="Find an open table in one game store and hold it for a session, without giving that table to two groups.",
    description="The hand-written contract is openapi.yaml at the repository root. This page is generated from the code and should agree with it.",
)

errors.install(app)
app.include_router(tables.router)
app.include_router(reservations.router)


@app.get("/health", tags=["Operational"], summary="Health check", include_in_schema=False)
def health():
    return {"status": "ok"}
