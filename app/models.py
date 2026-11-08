"""Pydantic models, typed from openapi.yaml's components/schemas.

Field descriptions are copied from the spec so /docs says the same thing.
A reservation with read-only fields is two models: ReservationCreate is what a
client sends, and Reservation is what the service returns.
"""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

GameTag = Literal["board_game", "card_game", "miniature", "roleplaying", "puzzle"]
Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class OpenHours(BaseModel):
    """One day's local clock hours. A weekday absent from a table's open_hours is closed."""

    weekday: Weekday = Field(description="A day name in English, lowercase.")
    opens: str = Field(
        pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$",
        description="Local opening time, 24-hour HH:MM.",
        examples=["09:00"],
    )
    closes: str = Field(
        pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$",
        description="Local closing time, 24-hour HH:MM. Later than opens.",
        examples=["22:00"],
    )


class Table(BaseModel):
    """A table on the floor. Tables are seeded by the store and read-only in v1."""

    table_id: str = Field(
        description="Opaque id. Not a counter, so a caller cannot walk every table by incrementing it.",
        examples=["tbl_7f3k9q2d"],
    )
    name: str = Field(min_length=1, max_length=80, description='Name posted at the table, for example "Table 4".', examples=["Table 4"])
    seats: int = Field(ge=1, le=12, description="How many players can sit here.", examples=[4])
    zone: str = Field(
        min_length=1,
        max_length=40,
        description='Where the table is in the store. A floor label may be "LL" or "M", not a number.',
        examples=["back room"],
    )
    game_tags: list[GameTag] = Field(description="Games this table is set up for. May be empty.")
    wheelchair_accessible: bool = Field(description="True when a wheelchair user can sit at this table.", examples=[True])
    time_zone: str = Field(
        description="IANA time zone of the store. Reservation instants are returned with an offset in this zone.",
        examples=["America/Chicago"],
    )
    open_hours: list[OpenHours] = Field(description="Local hours the table can be reserved. A missing weekday means the table is closed that day.")


class Requester(BaseModel):
    """The player who holds the table. One name field, so a single name or a long name is valid."""

    display_name: str = Field(
        min_length=1,
        max_length=200,
        description="The name the player goes by, as one field. Any script, spaces, and apostrophes are valid. There is no separate first and last name.",
        examples=["Trần Minh Anh"],
    )
    email: str = Field(
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Where a confirmation is sent. A shared household or club address is valid.",
        examples=["tran.minhanh@example.edu"],
    )


class ReservationCreate(BaseModel):
    """Fields the player sends to hold a table. The table id comes from the path."""

    model_config = ConfigDict(extra="forbid")

    starts_at: AwareDatetime = Field(description="When the hold starts. An offset is required.", examples=["2026-11-07T18:00:00-06:00"])
    ends_at: AwareDatetime = Field(description="When the hold ends. One to six hours after starts_at.", examples=["2026-11-07T22:00:00-06:00"])
    title: str | None = Field(default=None, max_length=120, description="Optional name for the session.", examples=["Commander pod"])
    requester: Requester
    player_count: int | None = Field(default=None, ge=1, le=12, description="How many players are coming. Cannot be more than the table's seats.", examples=[4])

    @field_validator("title", "player_count", mode="before")
    @classmethod
    def reject_null(cls, value):
        """The spec allows omitting these fields. It does not allow null."""
        if value is None:
            raise ValueError("cannot be null; omit the field instead")
        return value


class Reservation(BaseModel):
    """A hold on one table. Cancelled reservations stay and keep status cancelled."""

    model_config = ConfigDict(extra="ignore")

    reservation_id: str = Field(description="Opaque id. Not a counter.", examples=["rsv_8s2k1m0v4q7x3n9bw5zc"])
    table_id: str = Field(description="The table this hold is for.", examples=["tbl_7f3k9q2d"])
    starts_at: AwareDatetime = Field(description="When the hold starts. An offset is required, for example 2026-11-07T18:00:00-06:00.")
    ends_at: AwareDatetime = Field(description="When the hold ends. Must be 1 to 6 hours after starts_at, inside open hours, and at most 14 days ahead.")
    title: str | None = Field(default=None, max_length=120, description="Optional name for the session, for example the game being played.")
    requester: Requester
    player_count: int | None = Field(default=None, ge=1, le=12, description="How many players are coming. Cannot be more than the table's seats.")
    status: Literal["confirmed", "cancelled"] = Field(description="confirmed while the hold stands. cancelled after a delete. Read-only.")
    created_at: AwareDatetime = Field(description="When the hold was created, with an offset. Read-only.")


class ReservationPatch(BaseModel):
    """Fields that can change on an existing hold. Send at least one."""

    model_config = ConfigDict(extra="forbid")

    starts_at: AwareDatetime | None = Field(default=None, description="New start. An offset is required. The overlap check runs again.")
    ends_at: AwareDatetime | None = Field(default=None, description="New end. An offset is required.")
    title: str | None = Field(default=None, max_length=120, description="New session name.")
    player_count: int | None = Field(default=None, ge=1, le=12, description="New player count. Cannot be more than the table's seats.")

    @field_validator("starts_at", "ends_at", "title", "player_count", mode="before")
    @classmethod
    def reject_null(cls, value):
        """The spec allows omitting these fields. It does not allow null."""
        if value is None:
            raise ValueError("cannot be null; omit the field instead")
        return value
