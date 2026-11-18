"""The last-resort handler: anything unanticipated leaves as a problem-details 500."""

from fastapi.testclient import TestClient

from app import store
from app.main import app


def test_an_unhandled_error_is_a_500_problem_with_no_internals(monkeypatch):
    """Traceable to the review: "I would add an additional operation or a new kind of error
    that diverges it from the working example." The 500 problem is that new kind of error.
    It also covers app/errors.py lines 162-163, which the first coverage run listed as Missing.
    """

    def broken(table_id):
        raise RuntimeError("secret internal detail: store connection string")

    monkeypatch.setattr(store, "reservations_for", broken)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/v1/tables/tbl_7f3k9q2d/reservations")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    problem = response.json()
    assert set(problem) == {"type", "title", "status", "detail", "instance"}
    assert problem["status"] == 500
    assert problem["instance"] == "/v1/tables/tbl_7f3k9q2d/reservations"
    assert "secret" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text
