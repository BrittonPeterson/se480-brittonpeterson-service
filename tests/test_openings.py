"""Unit tests for GET /v1/tables/{table_id}/openings."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import TABLE, body, window

TZ = ZoneInfo("America/Chicago")


def day(offset: int = 2) -> str:
    return (datetime.now(TZ) + timedelta(days=offset)).date().isoformat()


def openings(client, **params):
    return client.get(f"/v1/tables/{TABLE}/openings", params={"date": day(), **params})


def hold(client, hour: int, length_hours: int = 2):
    starts_at, ends_at = window(hour=hour, length_hours=length_hours)
    response = client.post(f"/v1/tables/{TABLE}/reservations", json=body(starts_at, ends_at))
    assert response.status_code == 201
    return response.json()


def clock(stretch: dict) -> tuple[str, str]:
    return stretch["starts_at"][11:16], stretch["ends_at"][11:16]


def test_an_empty_day_is_one_stretch_from_open_to_close(client):
    response = openings(client)
    assert response.status_code == 200
    assert [clock(row) for row in response.json()] == [("09:00", "22:00")]


def test_a_hold_splits_the_day(client):
    hold(client, hour=12)
    assert [clock(row) for row in openings(client).json()] == [("09:00", "12:00"), ("14:00", "22:00")]


def test_min_length_drops_short_stretches(client):
    hold(client, hour=12)
    response = openings(client, min_length_minutes=240)
    assert [clock(row) for row in response.json()] == [("14:00", "22:00")]


def test_a_cancelled_hold_frees_its_window(client):
    created = hold(client, hour=12)
    client.delete(f"/v1/reservations/{created['reservation_id']}")
    assert [clock(row) for row in openings(client).json()] == [("09:00", "22:00")]


def test_openings_come_back_in_the_table_zone(client):
    row = openings(client).json()[0]
    assert row["starts_at"].endswith(("-05:00", "-06:00"))


def test_today_never_offers_time_that_has_passed(client):
    response = client.get(f"/v1/tables/{TABLE}/openings", params={"date": day(0)})
    assert response.status_code == 200
    now = datetime.now(TZ)
    assert all(datetime.fromisoformat(row["starts_at"]) >= now for row in response.json())


def test_a_past_date_is_400(client):
    response = client.get(f"/v1/tables/{TABLE}/openings", params={"date": day(-1)})
    assert response.status_code == 400
    assert response.json()["errors"] == [{"field": "date", "message": "must be today or later"}]


def test_a_date_past_14_days_is_400(client):
    response = client.get(f"/v1/tables/{TABLE}/openings", params={"date": day(30)})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "date"


def test_missing_date_is_400(client):
    response = client.get(f"/v1/tables/{TABLE}/openings")
    assert response.status_code == 400
    assert response.json()["errors"][0] == {"field": "date", "message": "is required"}


def test_min_length_below_an_hour_is_400(client):
    response = openings(client, min_length_minutes=30)
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "min_length_minutes"


def test_unknown_table_is_404(client):
    response = client.get("/v1/tables/tbl_00000000/openings", params={"date": day()})
    assert response.status_code == 404
    assert response.json()["type"].endswith("/not-found")
