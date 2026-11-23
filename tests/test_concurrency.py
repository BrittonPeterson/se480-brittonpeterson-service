"""Lab 5, task 6: the failure that matters, reproduced on demand.

Two players ask for the same table and window, and the requests are in flight
together. Each one runs the overlap check before either hold is stored, so each
one passes it. The barrier below is what makes that happen every time: it holds
both requests just after the check and releases them together. The window is
widened here, in the test, and never in the service.

The test is a strict expected failure: CI stays green while the failure stands
and goes red the day the test passes. That day the marker comes off and this
file becomes the proof that the fix holds.

Run just this one with: python -m pytest tests/test_concurrency.py -rxX
"""

import threading

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app import rules, store
from app.main import app
from tests.conftest import TABLE, body, window

KNOWN_LIMIT = (
    "Known limit: the overlap check and the write are two steps with nothing holding "
    "the table between them. Reproduced in Lab 5; the fix is a Week 6 decision."
)


@pytest.mark.xfail(strict=True, reason=KNOWN_LIMIT)
def test_two_requests_in_flight_together_cannot_both_hold_the_table(monkeypatch):
    store.reset()
    both_have_checked = threading.Barrier(2)
    real_find_conflict = rules.find_conflict

    def find_conflict_then_wait(*args, **kwargs):
        found = real_find_conflict(*args, **kwargs)
        try:
            # Wait for the other request to finish its own check. If it never
            # arrives (a fix that lets one request in at a time), stop waiting.
            both_have_checked.wait(timeout=2)
        except threading.BrokenBarrierError:
            pass
        return found

    monkeypatch.setattr(rules, "find_conflict", find_conflict_then_wait)
    conflicts_before = REGISTRY.get_sample_value("table_conflicts_total") or 0.0
    starts_at, ends_at = window()
    statuses: list[int] = []

    def hold():
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(f"/v1/tables/{TABLE}/reservations", json=body(starts_at, ends_at))
        statuses.append(response.status_code)

    requests = [threading.Thread(target=hold) for _ in range(2)]
    for request in requests:
        request.start()
    for request in requests:
        request.join(timeout=10)

    held = [r for r in store.reservations_for(TABLE) if r.status == "confirmed"]
    conflicts_after = REGISTRY.get_sample_value("table_conflicts_total") or 0.0
    store.reset()
    # What a correct service does: one 201, one 409, one hold, one conflict counted.
    assert sorted(statuses) == [201, 409]
    assert len(held) == 1
    assert conflicts_after == conflicts_before + 1
