"""Reproduce the failure that matters over real HTTP: two groups, one table.

For each of N windows, two threads wait at a barrier and then send the same
hold at the same moment. A correct service answers one 201 and one 409. Every
pair that gets two 201s is a double booking. The script prints each pair's
statuses and request ids, then /health and table_conflicts_total so you can
see what the service's own signals said, and cancels everything it created.

    python scripts/double_hold.py http://127.0.0.1:8000
    python scripts/double_hold.py https://se480-brittonpeterson-service.onrender.com 20

Nothing in the service is changed or slowed to make this happen. Over a
network the two requests have to land inside the same few milliseconds, so
not every pair races; tests/test_concurrency.py forces the overlap every time.
"""

import sys
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx2 as httpx

TABLE = "tbl_7f3k9q2d"
TZ = ZoneInfo("America/Chicago")


def windows(count: int) -> list[tuple[str, str]]:
    """Distinct one-hour windows from tomorrow on, inside 09:00-22:00."""
    out = []
    today = datetime.now(TZ).date()
    for i in range(count):
        day = today + timedelta(days=1 + i // 12)
        start = datetime(day.year, day.month, day.day, 9 + i % 12, tzinfo=TZ)
        out.append((start.isoformat(), (start + timedelta(hours=1)).isoformat()))
    return out


def conflicts(api: httpx.Client) -> float:
    for line in api.get("/metrics").text.splitlines():
        if line.startswith("table_conflicts_total "):
            return float(line.split()[1])
    return 0.0


def race(api: httpx.Client, starts_at: str, ends_at: str) -> list[httpx.Response]:
    hold = {
        "starts_at": starts_at,
        "ends_at": ends_at,
        "requester": {"display_name": "Race test", "email": "race@example.edu"},
    }
    gate = threading.Barrier(2)
    responses: list[httpx.Response] = []

    def send():
        gate.wait()
        responses.append(api.post(f"/v1/tables/{TABLE}/reservations", json=hold))

    threads = [threading.Thread(target=send) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return responses


def main(base_url: str, pairs: int) -> None:
    with httpx.Client(base_url=base_url, timeout=90) as api:
        print(f"Waking {base_url} ...")
        print("  /health before:", api.get("/health").json())
        before = conflicts(api)
        doubled = 0
        created = []
        for starts_at, ends_at in windows(pairs):
            responses = race(api, starts_at, ends_at)
            statuses = sorted(r.status_code for r in responses)
            ids = [r.headers.get("x-request-id") for r in responses]
            mark = "DOUBLE BOOKED" if statuses == [201, 201] else ""
            doubled += mark != ""
            print(f"  {starts_at[5:16]}  {statuses}  request ids {ids}  {mark}")
            created += [r.headers["location"] for r in responses if r.status_code == 201]
        after = conflicts(api)
        print(f"\n{doubled} of {pairs} pairs were both given the table.")
        print(f"table_conflicts_total moved by {after - before:g} (one per pair that was refused).")
        print("  /health after:", api.get("/health").json())
        for location in created:
            api.delete(location)
        print(f"Cancelled the {len(created)} holds this script created.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    main(sys.argv[1].rstrip("/"), int(sys.argv[2]) if len(sys.argv) == 3 else 20)
