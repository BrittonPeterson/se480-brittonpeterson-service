"""Unit tests for the table operations: the happy path and each declared error."""

from tests.conftest import OTHER_TABLE, TABLE

PROBLEM = "application/problem+json"


def test_list_tables_returns_every_table(client):
    response = client.get("/v1/tables")
    assert response.status_code == 200
    tables = response.json()
    assert {table["table_id"] for table in tables} >= {TABLE, OTHER_TABLE}
    assert all("name" in table and "seats" in table and "open_hours" in table for table in tables)


def test_seats_filter_keeps_only_big_enough_tables(client):
    response = client.get("/v1/tables", params={"seats_min": 8})
    assert response.status_code == 200
    assert [table["table_id"] for table in response.json()] == [OTHER_TABLE]


def test_wheelchair_filter(client):
    response = client.get("/v1/tables", params={"wheelchair_accessible": True})
    assert response.status_code == 200
    assert all(table["wheelchair_accessible"] for table in response.json())
    assert response.json()[0]["table_id"] == TABLE


def test_seats_below_one_is_a_validation_problem(client):
    response = client.get("/v1/tables", params={"seats_min": 0})
    assert response.status_code == 400
    assert response.headers["content-type"].startswith(PROBLEM)
    problem = response.json()
    assert problem["type"].endswith("/validation-failed")
    assert problem["status"] == 400
    assert problem["errors"][0]["field"] == "seats_min"


def test_get_one_table(client):
    response = client.get(f"/v1/tables/{TABLE}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Table 4"
    assert body["game_tags"] == ["card_game"]
    assert body["time_zone"] == "America/Chicago"


def test_unknown_table_is_not_found(client):
    response = client.get("/v1/tables/tbl_00000000")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM)
    problem = response.json()
    assert problem["type"].endswith("/not-found")
    assert "tbl_00000000" in problem["detail"]
    assert problem["instance"] == "/v1/tables/tbl_00000000"


def test_undefined_path_is_still_a_problem_body(client):
    response = client.get("/v1/nothing-here")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM)


def test_post_to_tables_is_405_and_lists_get(client):
    response = client.post("/v1/tables")
    assert response.status_code == 405
    assert response.headers["content-type"].startswith(PROBLEM)
    assert "GET" in response.headers["allow"]
