"""An in-memory store: seeded tables and a dict of reservations.

It loses every reservation when the process restarts. On Render's free
instance that happens after about fifteen idle minutes. That is Week 5's problem.
"""

import secrets
import string

from app.models import OpenHours, Table, Reservation

_ALPHABET = string.ascii_lowercase + string.digits
_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def new_id(prefix: str, length: int) -> str:
    """Opaque random ids. Never a counter."""
    return prefix + "_" + "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _week() -> list[OpenHours]:
    return [OpenHours(weekday=day, opens="09:00", closes="22:00") for day in _DAYS]


TABLES: dict[str, Table] = {
    "tbl_7f3k9q2d": Table(
        table_id="tbl_7f3k9q2d",
        name="Table 4",
        seats=4,
        zone="back room",
        game_tags=["card_game"],
        wheelchair_accessible=True,
        time_zone="America/Chicago",
        open_hours=_week(),
    ),
    "tbl_2c8v5n1p": Table(
        table_id="tbl_2c8v5n1p",
        name="Table 12",
        seats=8,
        zone="front window",
        game_tags=["board_game"],
        wheelchair_accessible=False,
        time_zone="America/Chicago",
        open_hours=_week(),
    ),
}

RESERVATIONS: dict[str, Reservation] = {}


def reset() -> None:
    """Forget every reservation. Tests call this between cases. Tables stay."""
    RESERVATIONS.clear()


def reservations_for(table_id: str) -> list[Reservation]:
    return [row for row in RESERVATIONS.values() if row.table_id == table_id]
