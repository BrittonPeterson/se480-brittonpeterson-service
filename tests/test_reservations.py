"""Unit tests for the reservation operations.

Each test asserts the status, the body shape, and, for an error, the problem body.
"""

from tests.conftest import TABLE, body, window

PROBLEM = "application/problem+json"


def create(client, **extra):
    starts_at, ends_at = window()
    payload = body(starts_at, ends_at)
    payload.update(extra)
    return client.post(f"/v1/tables/{TABLE}/reservations", json=payload)


def test_create_returns_201_with_location(client):
    response = create(client)
    assert response.status_code == 201
    created = response.json()
    assert response.headers["location"] == f"/v1/reservations/{created['reservation_id']}"
    assert created["reservation_id"].startswith("rsv_")
    assert created["table_id"] == TABLE
    assert created["status"] == "confirmed"
    assert created["requester"]["display_name"] == "Trần Minh Anh"
    assert created["starts_at"].endswith(("-05:00", "-06:00"))


def test_create_without_offset_is_400_naming_the_field(client):
    response = client.post(
        f"/v1/tables/{TABLE}/reservations",
        json=body("2026-11-07T18:00:00", "2026-11-07T20:00:00"),
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith(PROBLEM)
    fields = {err["field"] for err in response.json()["errors"]}
    assert "starts_at" in fields
    assert "offset" in next(err["message"] for err in response.json()["errors"] if err["field"] == "starts_at")


def test_create_with_end_before_start_is_400(client):
    starts_at, ends_at = window()
    response = client.post(f"/v1/tables/{TABLE}/reservations", json=body(ends_at, starts_at))
    assert response.status_code == 400
    assert response.json()["errors"][0] == {"field": "ends_at", "message": "must be later than starts_at"}


def test_create_over_capacity_is_400(client):
    response = create(client, player_count=5)
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "player_count"


def test_create_on_unknown_table_is_404(client):
    starts_at, ends_at = window()
    response = client.post("/v1/tables/tbl_00000000/reservations", json=body(starts_at, ends_at))
    assert response.status_code == 404
    assert response.json()["type"].endswith("/not-found")


def test_overlapping_window_is_409_without_the_other_group(client):
    first = create(client)
    assert first.status_code == 201
    second = create(client)
    assert second.status_code == 409
    assert second.headers["content-type"].startswith(PROBLEM)
    problem = second.json()
    assert problem["type"].endswith("/table-conflict")
    assert problem["status"] == 409
    assert problem["conflicts_with"]["starts_at"] == first.json()["starts_at"]
    assert "requester" not in problem["conflicts_with"]
    assert "Table 4" in problem["detail"]


def test_adjacent_windows_do_not_conflict(client):
    starts_at, ends_at = window(hour=12, length_hours=2)
    later_start, later_end = window(hour=14, length_hours=2)
    assert client.post(f"/v1/tables/{TABLE}/reservations", json=body(starts_at, ends_at)).status_code == 201
    assert client.post(f"/v1/tables/{TABLE}/reservations", json=body(later_start, later_end)).status_code == 201


def test_get_reservation(client):
    created = create(client).json()
    response = client.get(f"/v1/reservations/{created['reservation_id']}")
    assert response.status_code == 200
    assert response.json()["reservation_id"] == created["reservation_id"]


def test_unknown_reservation_is_404(client):
    response = client.get("/v1/reservations/rsv_00000000000000000000")
    assert response.status_code == 404
    assert response.json()["type"].endswith("/not-found")


def test_list_includes_a_cancelled_reservation(client):
    created = create(client).json()
    client.delete(f"/v1/reservations/{created['reservation_id']}")
    listed = client.get(f"/v1/tables/{TABLE}/reservations")
    assert listed.status_code == 200
    assert listed.json()[0]["status"] == "cancelled"


def test_window_lists_the_overlapping_reservation(client):
    created = create(client).json()
    starts_at, ends_at = window()
    listed = client.get(
        f"/v1/tables/{TABLE}/reservations",
        params={"window_start": starts_at, "window_end": ends_at},
    )
    assert [row["reservation_id"] for row in listed.json()] == [created["reservation_id"]]


def test_window_with_only_one_bound_is_400(client):
    starts_at, _ = window()
    response = client.get(f"/v1/tables/{TABLE}/reservations", params={"window_start": starts_at})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "window_start"


def test_list_on_unknown_table_is_404(client):
    response = client.get("/v1/tables/tbl_00000000/reservations")
    assert response.status_code == 404
    assert response.json()["type"].endswith("/not-found")


def test_patch_retitles_and_keeps_the_window(client):
    created = create(client).json()
    response = client.patch(
        f"/v1/reservations/{created['reservation_id']}",
        json={"title": "Commander pod, later start"},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Commander pod, later start"
    assert response.json()["starts_at"] == created["starts_at"]


def test_patch_with_no_fields_is_400(client):
    created = create(client).json()
    response = client.patch(f"/v1/reservations/{created['reservation_id']}", json={})
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == "body"


def test_patch_unknown_reservation_is_404(client):
    response = client.patch("/v1/reservations/rsv_00000000000000000000", json={"title": "nope"})
    assert response.status_code == 404
    assert response.json()["type"].endswith("/not-found")


def test_patch_into_another_reservation_is_409(client):
    first = create(client).json()
    later_start, later_end = window(hour=16, length_hours=2)
    second = client.post(f"/v1/tables/{TABLE}/reservations", json=body(later_start, later_end)).json()
    response = client.patch(
        f"/v1/reservations/{second['reservation_id']}",
        json={"starts_at": first["starts_at"], "ends_at": first["ends_at"]},
    )
    assert response.status_code == 409
    assert response.json()["conflicts_with"]["starts_at"] == first["starts_at"]


def test_delete_is_204_and_repeatable(client):
    created = create(client).json()
    path = f"/v1/reservations/{created['reservation_id']}"
    assert client.delete(path).status_code == 204
    assert client.delete(path).status_code == 204
    assert client.get(path).json()["status"] == "cancelled"


def test_delete_of_never_issued_id_is_404(client):
    response = client.delete("/v1/reservations/rsv_00000000000000000000")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM)


def test_cancelled_slot_can_be_held_again(client):
    created = create(client).json()
    client.delete(f"/v1/reservations/{created['reservation_id']}")
    assert create(client).status_code == 201
