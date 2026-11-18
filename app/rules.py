"""The business rules from the design sheet, as plain functions.

Nothing here imports FastAPI. Routers parse the request, call a rule, and
shape the response. Each *_errors function returns problem-details errors
entries; an empty list means the request passes that rule.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

MIN_LENGTH = timedelta(hours=1)
MAX_LENGTH = timedelta(hours=6)
MAX_AHEAD = timedelta(days=14)


def window_errors(
    starts_at: datetime, ends_at: datetime, now: datetime, *, check_past: bool = True
) -> list[dict]:
    """Rule violations in a requested window.

    check_past is off when a patch keeps the old start, so a session already
    under way can still be retitled.
    """
    errors = []
    if check_past and starts_at < now:
        errors.append({"field": "starts_at", "message": "must not be in the past"})
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


def hours_on(day: date, open_hours):
    """That weekday's open hours, or None when the table is closed that day."""
    weekday = day.strftime("%A").lower()
    return next((row for row in open_hours if row.weekday == weekday), None)


def open_hours_errors(
    starts_at: datetime, ends_at: datetime, time_zone: str, open_hours
) -> list[dict]:
    """The window must fall on one open day, between that day's opens and closes."""
    tz = ZoneInfo(time_zone)
    start = starts_at.astimezone(tz)
    end = ends_at.astimezone(tz)
    if start.date() != end.date():
        return [
            {
                "field": "ends_at",
                "message": "must finish the same day, inside the table's open hours",
            }
        ]
    hours = hours_on(start.date(), open_hours)
    if hours is None:
        return [{"field": "starts_at", "message": f"the table is closed on {start:%A}"}]
    if start.time() < time.fromisoformat(hours.opens) or end.time() > time.fromisoformat(
        hours.closes
    ):
        return [
            {
                "field": "starts_at",
                "message": f"must be inside open hours, {hours.opens} to {hours.closes}",
            }
        ]
    return []


def seat_errors(player_count: int | None, seats: int, table_name: str) -> list[dict]:
    """More players than chairs is a rule the schema's 1 to 12 range cannot see."""
    if player_count is not None and player_count > seats:
        return [{"field": "player_count", "message": f"{table_name} seats {seats}"}]
    return []


def patch_errors(changes: dict, status: str) -> list[dict]:
    """A patch must change something, and only a confirmed hold can change."""
    if not changes:
        return [
            {
                "field": "body",
                "message": "send at least one of starts_at, ends_at, title, or player_count",
            }
        ]
    if status == "cancelled":
        return [
            {
                "field": "status",
                "message": "a cancelled reservation cannot be changed. Create a new one.",
            }
        ]
    return []


def list_window_errors(window_start: datetime | None, window_end: datetime | None) -> list[dict]:
    """A list window needs both bounds, in order. Neither bound means no window."""
    if window_start is None and window_end is None:
        return []
    if window_start is None or window_end is None:
        return [{"field": "window_start", "message": "send window_start and window_end together"}]
    if window_end <= window_start:
        return [{"field": "window_end", "message": "must be later than window_start"}]
    return []


def openings_day_errors(day: date, now: datetime) -> list[dict]:
    """Openings are offered for today through the last bookable day."""
    if day < now.date():
        return [{"field": "date", "message": "must be today or later"}]
    if day > (now + MAX_AHEAD).date():
        return [{"field": "date", "message": "must be within the next 14 days"}]
    return []


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Two windows overlap when each starts before the other ends. Touching edges do not."""
    return a_start < b_end and a_end > b_start


def free_stretches(
    opens: datetime, closes: datetime, busy: list[tuple[datetime, datetime]], min_length: timedelta
) -> list[tuple[datetime, datetime]]:
    """The gaps between busy windows inside [opens, closes], each at least min_length long."""
    stretches = []
    cursor = opens
    for start, end in sorted(busy):
        if start >= closes:
            break
        if start - cursor >= min_length:
            stretches.append((cursor, start))
        cursor = max(cursor, end)
    if closes - cursor >= min_length:
        stretches.append((cursor, closes))
    return stretches


def openings(
    day: date,
    now: datetime,
    time_zone: str,
    open_hours,
    busy: list[tuple[datetime, datetime]],
    min_length: timedelta,
) -> list[tuple[datetime, datetime]]:
    """Free stretches on one local day, in the table's zone, that a hold could still start in.

    Today's stretches start at the next quarter hour. A stretch that starts
    after the 14-day limit is left out.
    """
    tz = ZoneInfo(time_zone)
    hours = hours_on(day, open_hours)
    if hours is None:
        return []
    opens = datetime.combine(day, time.fromisoformat(hours.opens), tzinfo=tz)
    closes = datetime.combine(day, time.fromisoformat(hours.closes), tzinfo=tz)
    local_now = now.astimezone(tz)
    next_quarter = local_now.replace(second=0, microsecond=0) + timedelta(
        minutes=15 - local_now.minute % 15
    )
    stretches = free_stretches(max(opens, next_quarter), closes, busy, min_length)
    latest_start = now + MAX_AHEAD
    return [
        (start.astimezone(tz), end.astimezone(tz))
        for start, end in stretches
        if start <= latest_start
    ]


def find_conflict(
    starts_at: datetime, ends_at: datetime, reservations, *, ignore_id: str | None = None
):
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
