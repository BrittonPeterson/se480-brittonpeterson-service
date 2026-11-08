"""The business rules from the design sheet, as plain functions.

Nothing here imports FastAPI. Routers parse the request, call a rule, and
shape the response.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

MIN_LENGTH = timedelta(hours=1)
MAX_LENGTH = timedelta(hours=6)
MAX_AHEAD = timedelta(days=14)


def window_errors(starts_at: datetime, ends_at: datetime, now: datetime) -> list[dict]:
    """Rule violations in a requested window, as problem-details errors entries."""
    errors = []
    if ends_at <= starts_at:
        errors.append({"field": "ends_at", "message": "must be later than starts_at"})
        return errors
    length = ends_at - starts_at
    if length < MIN_LENGTH:
        errors.append({"field": "ends_at", "message": "must be at least 1 hour after starts_at"})
    if length > MAX_LENGTH:
        errors.append({"field": "ends_at", "message": "must be at most 6 hours after starts_at"})
    if starts_at > now + MAX_AHEAD:
        errors.append({"field": "starts_at", "message": "must be within the next 14 days"})
    return errors


def open_hours_errors(starts_at: datetime, ends_at: datetime, time_zone: str, open_hours) -> list[dict]:
    """The window must fall on one open day, between that day's opens and closes."""
    tz = ZoneInfo(time_zone)
    start = starts_at.astimezone(tz)
    end = ends_at.astimezone(tz)
    if start.date() != end.date():
        return [{"field": "ends_at", "message": "must finish the same day, inside the table's open hours"}]
    weekday = start.strftime("%A").lower()
    hours = next((row for row in open_hours if row.weekday == weekday), None)
    if hours is None:
        return [{"field": "starts_at", "message": f"the table is closed on {weekday}"}]
    opens = time.fromisoformat(hours.opens)
    closes = time.fromisoformat(hours.closes)
    if start.time() < opens or end.time() > closes:
        return [{
            "field": "starts_at",
            "message": f"must be inside open hours, {hours.opens} to {hours.closes}",
        }]
    return []


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Two windows overlap when each starts before the other ends. Touching edges do not."""
    return a_start < b_end and a_end > b_start


def find_conflict(starts_at: datetime, ends_at: datetime, reservations, *, ignore_id: str | None = None):
    """The first confirmed reservation overlapping the window, or None.

    Two requests that both run this check before either is stored will both
    pass. That is the seeded failure. v1 does not lock the table.
    """
    for existing in reservations:
        if existing.status != "confirmed" or existing.reservation_id == ignore_id:
            continue
        if overlaps(starts_at, ends_at, existing.starts_at, existing.ends_at):
            return existing
    return None
