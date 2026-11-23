"""Lab 5: the service says what it is doing, and says nothing it should not."""

import json
import re

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app import observability, store
from app.main import app
from app.observability import REQUEST_ID_HEADER, UNMATCHED
from tests.conftest import TABLE, body, window

FIELDS = ["ts", "level", "request_id", "method", "route", "status", "duration_ms"]


def logged(capsys) -> list[dict]:
    """Every JSON log line written to standard output since the last call."""
    out = capsys.readouterr().out
    return [json.loads(line) for line in out.splitlines() if line.startswith("{")]


def counted(route: str, status: str) -> float:
    labels = {"route": route, "status": status}
    return REGISTRY.get_sample_value("http_requests_total", labels) or 0.0


def test_one_line_per_request_with_its_fields(client, capsys):
    capsys.readouterr()
    response = client.get("/v1/tables")
    lines = logged(capsys)
    assert len(lines) == 1
    line = lines[0]
    assert list(line) == FIELDS
    assert line["ts"].endswith("Z")
    assert (line["level"], line["method"], line["route"], line["status"]) == (
        "INFO",
        "GET",
        "/v1/tables",
        200,
    )
    assert isinstance(line["duration_ms"], int | float)
    assert line["duration_ms"] >= 0
    assert line["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_a_404_logs_the_route_template_never_the_reservation_id(client, capsys):
    capsys.readouterr()
    response = client.get("/v1/reservations/rsv_doesnotexist00000000")
    assert response.status_code == 404
    out = capsys.readouterr().out
    assert "rsv_doesnotexist" not in out
    line = json.loads(out.splitlines()[-1])
    assert line["route"] == "/v1/reservations/{reservation_id}"
    assert line["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_a_create_logs_no_name_email_or_body(client, capsys):
    starts_at, ends_at = window()
    capsys.readouterr()
    response = client.post(f"/v1/tables/{TABLE}/reservations", json=body(starts_at, ends_at))
    assert response.status_code == 201
    out = capsys.readouterr().out
    for private in ("Trần Minh Anh", "Tr\\u1ea7n", "tran.minhanh", "Commander pod"):
        assert private not in out
    assert response.json()["reservation_id"] not in out
    assert json.loads(out.splitlines()[-1])["route"] == "/v1/tables/{table_id}/reservations"


def test_a_path_nobody_defined_gets_one_fixed_label(client, capsys):
    capsys.readouterr()
    response = client.get("/v1/nothing/here/private-123")
    out = capsys.readouterr().out
    assert "private-123" not in out
    line = json.loads(out.splitlines()[-1])
    assert line["route"] == UNMATCHED
    assert line["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_a_500_still_has_its_id_and_its_line(monkeypatch, capsys, caplog):
    def explode(_table_id):
        raise RuntimeError("the store fell over")

    monkeypatch.setattr(store, "reservations_for", explode)
    capsys.readouterr()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/v1/tables/{TABLE}/reservations")
    assert response.status_code == 500
    rid = response.headers[REQUEST_ID_HEADER]
    line = logged(capsys)[-1]
    assert (line["level"], line["status"]) == ("ERROR", 500)
    assert line["route"] == "/v1/tables/{table_id}/reservations"
    assert line["request_id"] == rid
    assert rid in response.json()["detail"]
    traceback_record = next(r for r in caplog.records if r.name == "app")
    assert f"request_id={rid}" in traceback_record.getMessage()
    assert "route=/v1/tables/{table_id}/reservations" in traceback_record.getMessage()


def test_an_incoming_id_is_kept_only_if_it_looks_like_one(client):
    kept = client.get("/v1/tables", headers={REQUEST_ID_HEADER: "abc12345-from-caller"})
    assert kept.headers[REQUEST_ID_HEADER] == "abc12345-from-caller"
    replaced = client.get("/v1/tables", headers={REQUEST_ID_HEADER: 'x","level":"FAKE'})
    assert re.fullmatch(r"[0-9a-f]{16}", replaced.headers[REQUEST_ID_HEADER])


def test_health_says_when_it_started_and_what_it_holds(client):
    starts_at, ends_at = window()
    created = client.post(f"/v1/tables/{TABLE}/reservations", json=body(starts_at, ends_at))
    client.delete(created.headers["location"])
    client.post(f"/v1/tables/{TABLE}/reservations", json=body(starts_at, ends_at))
    report = client.get("/health").json()
    assert set(report) == {"status", "started_at", "uptime_seconds", "commit", "store"}
    assert report["status"] == "ok"
    assert report["uptime_seconds"] >= 0
    assert report["commit"] == "unknown"
    assert report["store"] == {"tables": 2, "reservations": 2, "confirmed": 1}


def test_health_reports_the_render_commit_when_it_is_set(client, monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "9d4e9ca5b8739f04bc2b4a0a45a43157128583bf")
    assert client.get("/health").json()["commit"] == "9d4e9ca"


def test_health_and_metrics_are_not_logged_or_counted(client, capsys):
    capsys.readouterr()
    client.get("/health")
    client.get("/metrics")
    assert logged(capsys) == []
    assert counted("/health", "2xx") == 0.0
    assert counted("/metrics", "2xx") == 0.0


def test_a_request_moves_its_counter(client):
    # The registry is shared by the whole process, so assert on the change.
    before = counted("/v1/tables", "2xx")
    client.get("/v1/tables")
    assert counted("/v1/tables", "2xx") == before + 1


def test_metrics_is_served_in_the_prometheus_text_format(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in response.text
    assert 'http_request_duration_seconds_bucket{le="1.0"' in response.text
    assert "table_conflicts_total" in response.text


def test_the_startup_switch_refuses_to_start_only_when_set(monkeypatch):
    monkeypatch.delenv("LAB5_FAIL_STARTUP", raising=False)
    observability.fail_startup_if_asked()
    monkeypatch.setenv("LAB5_FAIL_STARTUP", "1")
    with pytest.raises(SystemExit):
        observability.fail_startup_if_asked()


def test_a_refused_hold_is_counted(client):
    before = REGISTRY.get_sample_value("table_conflicts_total") or 0.0
    starts_at, ends_at = window()
    path = f"/v1/tables/{TABLE}/reservations"
    assert client.post(path, json=body(starts_at, ends_at)).status_code == 201
    assert client.post(path, json=body(starts_at, ends_at)).status_code == 409
    assert REGISTRY.get_sample_value("table_conflicts_total") == before + 1
