"""Shared fixtures. Every test gets a fresh store and a client for the app."""

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app


@pytest.fixture
def client():
    store.reset()
    with TestClient(app) as test_client:
        yield test_client
    store.reset()


TABLE = "tbl_7f3k9q2d"
OTHER_TABLE = "tbl_2c8v5n1p"


def window(day_offset: int = 2, hour: int = 12, length_hours: int = 2) -> tuple[str, str]:
    """An aware RFC 3339 window inside open hours (09:00-22:00) and within 14 days."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/Chicago")
    day = (datetime.now(tz) + timedelta(days=day_offset)).date()
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz).replace(hour=hour)
    return start.isoformat(), (start + timedelta(hours=length_hours)).isoformat()


def body(starts_at: str, ends_at: str, **extra) -> dict:
    return {
        "starts_at": starts_at,
        "ends_at": ends_at,
        "title": "Commander pod",
        "requester": {"display_name": "Trần Minh Anh", "email": "tran.minhanh@example.edu"},
        "player_count": 4,
        **extra,
    }
