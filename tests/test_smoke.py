"""The Lab 1 smoke test: the service is up.

Lab 5 added fields to /health, so this checks the status and leaves the rest to
tests/test_observability.py.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
