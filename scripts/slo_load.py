"""Send a few hundred requests along the SLO's journey, then compute the SLI from /metrics.

The journey is a player finding a free table and holding it: list tables, list
a table's openings, list its reservations, create a hold (some on purpose into
a taken window, so the 409 path is measured too), and cancel it.

    python scripts/slo_load.py http://127.0.0.1:8000
    python scripts/slo_load.py https://se480-brittonpeterson-service.onrender.com 300

The SLI is read from the service's own counters, so it covers everything the
service has answered since /health's started_at, not only this script's
requests. It prints the arithmetic.
"""

import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx2 as httpx

TZ = ZoneInfo("America/Chicago")
TABLE = "tbl_7f3k9q2d"
JOURNEY = {
    "/v1/tables",
    "/v1/tables/{table_id}/openings",
    "/v1/tables/{table_id}/reservations",
    "/v1/reservations/{reservation_id}",
}
BOUND = "1.0"


def parse(text: str) -> dict[tuple[str, tuple], float]:
    samples = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        name_labels, value = line.rsplit(" ", 1)
        name, _, labels = name_labels.partition("{")
        pairs = tuple(
            tuple(part.split("=", 1)) for part in labels.rstrip("}").split(",") if "=" in part
        )
        samples[(name, tuple((k, v.strip('"')) for k, v in pairs))] = float(value)
    return samples


def sli(base_url: str) -> None:
    with httpx.Client(base_url=base_url, timeout=90) as api:
        health = api.get("/health").json()
        samples = parse(api.get("/metrics").text)
    valid = good = fast = count = 0.0
    for (name, labels), value in samples.items():
        label = dict(labels)
        if label.get("route") not in JOURNEY:
            continue
        if name == "http_requests_total":
            valid += value
            if label["status"] != "5xx":
                good += value
        elif name == "http_request_duration_seconds_bucket" and label["le"] == BOUND:
            fast += value
        elif name == "http_request_duration_seconds_count":
            count += value
    print(f"\nWindow: since started_at {health['started_at']} (commit {health['commit']}).")
    print(f"Not a 5xx:      {good:g} / {valid:g} = {100 * good / valid:.2f}%")
    print(f"Under {BOUND} s:    {fast:g} / {count:g} = {100 * fast / count:.2f}%")


def load(base_url: str, rounds: int) -> None:
    today = datetime.now(TZ).date()
    with httpx.Client(base_url=base_url, timeout=90) as api:
        print(f"Waking {base_url} ...", api.get("/health").json()["status"])
        sent = 0
        for i in range(rounds):
            day = today + timedelta(days=1 + i % 13)
            start = datetime(day.year, day.month, day.day, 9 + i % 12, 30, tzinfo=TZ)
            hold = {
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(hours=1)).isoformat(),
                "requester": {"display_name": "SLO load", "email": "slo@example.edu"},
            }
            api.get("/v1/tables", params={"seats_min": 2})
            api.get(f"/v1/tables/{TABLE}/openings", params={"date": day.isoformat()})
            created = api.post(f"/v1/tables/{TABLE}/reservations", json=hold)
            sent += 3
            if i % 4 == 0:
                api.post(f"/v1/tables/{TABLE}/reservations", json=hold)
                sent += 1
            api.get(f"/v1/tables/{TABLE}/reservations")
            sent += 1
            if created.status_code == 201:
                api.delete(created.headers["location"])
                sent += 1
        print(f"Sent {sent} requests along the journey.")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    url = sys.argv[1].rstrip("/")
    load(url, int(sys.argv[2]) if len(sys.argv) == 3 else 60)
    sli(url)
