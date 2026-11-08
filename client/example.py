"""The first consumer of Table Hold: list, create, and handle a conflict for a person.

Run against the deployed service (the first call may take about 30 seconds while Render wakes it):

    python client/example.py https://se480-brittonpeterson-service.onrender.com

or against a local server (python -m uvicorn app.main:app --port 8000):

    python client/example.py http://127.0.0.1:8000
"""

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx2 as httpx

TZ = ZoneInfo("America/Chicago")


def say(problem: dict) -> None:
    """Show a person what went wrong: sentences first, then the field list."""
    print(f"  Couldn't do that: {problem.get('title', 'unknown problem')}")
    if problem.get("detail"):
        print(f"  {problem['detail']}")
    for err in problem.get("errors") or []:
        print(f"  - {err['field']}: {err['message']}")
    if "conflicts_with" in problem:
        window = problem["conflicts_with"]
        print(f"  Taken from {window['starts_at']} to {window['ends_at']}.")
    print(f"  Raw body, for a developer: {problem}")


def main(base_url: str) -> None:
    print(f"Connecting to {base_url} (a sleeping service takes about 30 seconds to wake)...")
    with httpx.Client(base_url=base_url + "/v1", timeout=httpx.Timeout(60.0, connect=60.0)) as api:
        tables = api.get("/tables", params={"seats_min": 4})
        tables.raise_for_status()
        print("Tables that seat four or more:")
        for table in tables.json():
            print(f"  {table['table_id']}  {table['name']} ({table['zone']}, seats {table['seats']})")
        table_id = tables.json()[0]["table_id"]

        start = (datetime.now(TZ) + timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)
        booking = {
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=2)).isoformat(),
            "title": "Commander pod",
            "requester": {"display_name": "Trần Minh Anh", "email": "tran.minhanh@example.edu"},
            "player_count": 4,
        }

        print(f"\nHolding {table_id} from {start:%a %H:%M} for two hours...")
        first = api.post(f"/tables/{table_id}/reservations", json=booking)
        if first.status_code == 201:
            print(f"  Reserved. Reservation {first.json()['reservation_id']}; see {first.headers['location']}")
        else:
            say(first.json())
            return

        print("\nTrying the same window again, on purpose...")
        second = api.post(f"/tables/{table_id}/reservations", json=booking)
        if second.status_code == 409:
            say(second.json())
        else:
            print(f"  Unexpected: {second.status_code} {second.text}")

        print("\nCancelling the first one so the slot is free again...")
        gone = api.delete(first.headers["location"].removeprefix("/v1"))
        print(f"  Cancelled ({gone.status_code})." if gone.status_code == 204 else f"  Unexpected: {gone.status_code} {gone.text}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1].rstrip("/"))
