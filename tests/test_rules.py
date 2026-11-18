"""Unit tests for app/rules.py that need a table the store does not seed.

Both seeded tables are open every day, so a closed day can only be reached by
calling the rule directly with a shorter open_hours list.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app import rules
from app.models import OpenHours

TZ = ZoneInfo("America/Chicago")
WEEKDAYS_ONLY = [
    OpenHours(weekday=day, opens="09:00", closes="22:00")
    for day in ("monday", "tuesday", "wednesday", "thursday", "friday")
]
SUNDAY = date(2026, 11, 22)


def test_a_window_on_a_closed_day_is_rejected():
    """Covers app/rules.py line 62, which the first coverage run listed as Missing."""
    start = datetime(2026, 11, 22, 12, tzinfo=TZ)
    errors = rules.open_hours_errors(
        start, start + timedelta(hours=2), "America/Chicago", WEEKDAYS_ONLY
    )
    assert errors == [{"field": "starts_at", "message": "the table is closed on Sunday"}]


def test_a_closed_day_has_no_openings():
    """Covers app/rules.py line 159, which the first coverage run listed as Missing."""
    now = datetime(2026, 11, 20, 8, tzinfo=TZ)
    assert rules.openings(SUNDAY, now, "America/Chicago", WEEKDAYS_ONLY, [], rules.MIN_LENGTH) == []


def test_a_hold_after_closing_does_not_shorten_the_day():
    """Covers app/rules.py line 134: a busy window that starts at or after closing is ignored."""
    opens = datetime(2026, 11, 20, 9, tzinfo=TZ)
    closes = datetime(2026, 11, 20, 22, tzinfo=TZ)
    late = (closes, closes + timedelta(hours=1))
    assert rules.free_stretches(opens, closes, [late], rules.MIN_LENGTH) == [(opens, closes)]


def test_touching_windows_do_not_overlap():
    """The design sheet says touching edges do not overlap; this pins both directions."""
    noon = datetime(2026, 11, 20, 12, tzinfo=TZ)
    two = noon + timedelta(hours=2)
    four = noon + timedelta(hours=4)
    assert not rules.overlaps(noon, two, two, four)
    assert not rules.overlaps(two, four, noon, two)
    assert rules.overlaps(noon, two + timedelta(minutes=1), two, four)


def test_exactly_one_and_exactly_six_hours_are_allowed():
    """The length rule is inclusive at both ends: 1 hour and 6 hours both pass."""
    now = datetime(2026, 11, 18, 8, tzinfo=TZ)
    start = datetime(2026, 11, 20, 12, tzinfo=TZ)
    assert rules.window_errors(start, start + rules.MIN_LENGTH, now) == []
    assert rules.window_errors(start, start + rules.MAX_LENGTH, now) == []
