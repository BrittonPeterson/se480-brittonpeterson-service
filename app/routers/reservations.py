"""Reservations: list, create, get, update, and cancel."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Response

from app import rules, store
from app.errors import Conflict, NotFound, ProblemDetails, ValidationFailed
from app.models import Reservation, ReservationCreate, ReservationPatch, Table
from app.routers.tables import table_or_404

router = APIRouter(prefix="/v1", tags=["Reservations"])

PROBLEM = {"model": ProblemDetails, "content": {"application/problem+json": {}}}
VALIDATION = {400: {**PROBLEM, "description": "A field is missing, malformed, or breaks a rule. errors lists the fields."}}
NOT_FOUND = {404: {**PROBLEM, "description": "No table or reservation has that id."}}
CONFLICT = {409: {**PROBLEM, "description": "The table already has a confirmed reservation in that window."}}


def in_table_zone(reservation: Reservation, table: Table) -> Reservation:
    """The spec promises instants come back in the table's time zone."""
    tz = ZoneInfo(table.time_zone)
    return reservation.model_copy(update={
        "starts_at": reservation.starts_at.astimezone(tz),
        "ends_at": reservation.ends_at.astimezone(tz),
        "created_at": reservation.created_at.astimezone(tz),
    })


def reservation_or_404(reservation_id: str) -> Reservation:
    reservation = store.RESERVATIONS.get(reservation_id)
    if reservation is None:
        raise NotFound(
            f"No reservation has id {reservation_id}. The id is in the Location header of the response that created it."
        )
    return reservation


def check_window(
    table: Table,
    starts_at: datetime,
    ends_at: datetime,
    player_count: int | None,
    *,
    ignore_id: str | None = None,
    check_past: bool = True,
) -> None:
    """Rules first (400), then the table's state (409)."""
    errors = rules.window_errors(starts_at, ends_at, now=datetime.now(timezone.utc), check_past=check_past)
    errors += rules.open_hours_errors(starts_at, ends_at, table.time_zone, table.open_hours)
    if player_count is not None and player_count > table.seats:
        errors.append({"field": "player_count", "message": f"{table.name} seats {table.seats}"})
    if errors:
        raise ValidationFailed("Fix the fields under errors and try again.", errors=errors)

    conflict = rules.find_conflict(starts_at, ends_at, store.reservations_for(table.table_id), ignore_id=ignore_id)
    if conflict is not None:
        tz = ZoneInfo(table.time_zone)
        start, end = conflict.starts_at.astimezone(tz), conflict.ends_at.astimezone(tz)
        raise Conflict(
            f"{table.name} is held from {start:%H:%M} to {end:%H:%M} on {start:%a} {start.day} {start:%b %Y} ({table.time_zone}). "
            "Choose a time outside that window, or another table.",
            conflicts_with={"starts_at": start.isoformat(), "ends_at": end.isoformat()},
        )


@router.get(
    "/tables/{table_id}/reservations",
    operation_id="listTableReservations",
    summary="List reservations on one table",
    description="Returns reservations on the table, including cancelled ones. Pass a window to see what overlaps that block of time.",
    response_model=list[Reservation],
    response_model_exclude_none=True,
    responses={**VALIDATION, **NOT_FOUND},
)
def list_table_reservations(
    table_id: str,
    window_start: datetime | None = Query(default=None, description="Include reservations that overlap at or after this instant. Requires an offset."),
    window_end: datetime | None = Query(default=None, description="Include reservations that overlap at or before this instant. Requires an offset."),
) -> list[Reservation]:
    table = table_or_404(table_id)
    rows = store.reservations_for(table_id)
    if window_start is None and window_end is None:
        found = rows
    else:
        errors = []
        if window_start is None or window_end is None:
            errors.append({"field": "window_start", "message": "send window_start and window_end together"})
        for name, value in (("window_start", window_start), ("window_end", window_end)):
            if value is not None and value.tzinfo is None:
                errors.append({"field": name, "message": "needs an offset, for example 2026-11-07T18:00:00-06:00"})
        if errors:
            raise ValidationFailed("Fix the fields under errors and try again.", errors=errors)
        if window_end <= window_start:
            raise ValidationFailed(
                "Fix the fields under errors and try again.",
                errors=[{"field": "window_end", "message": "must be later than window_start"}],
            )
        found = [row for row in rows if rules.overlaps(window_start, window_end, row.starts_at, row.ends_at)]
    return [in_table_zone(row, table) for row in sorted(found, key=lambda row: row.starts_at)]


@router.post(
    "/tables/{table_id}/reservations",
    operation_id="createReservation",
    status_code=201,
    summary="Hold a table for a block of time",
    description=(
        "Creates a confirmed reservation when the window is inside open hours and does not overlap another confirmed reservation. "
        "The spec promises 409 when the windows overlap. v1 does not yet define the lock that keeps two near-simultaneous creates from both succeeding."
    ),
    response_model=Reservation,
    response_model_exclude_none=True,
    responses={
        **VALIDATION,
        **NOT_FOUND,
        **CONFLICT,
        201: {
            "description": "The table is held.",
            "headers": {"Location": {"description": "Path of the new reservation on the deployed service, including /v1.", "schema": {"type": "string"}}},
        },
    },
)
def create_reservation(table_id: str, body: ReservationCreate, response: Response) -> Reservation:
    table = table_or_404(table_id)
    check_window(table, body.starts_at, body.ends_at, body.player_count)
    reservation = Reservation(
        **body.model_dump(),
        reservation_id=store.new_id("rsv", 20),
        table_id=table_id,
        status="confirmed",
        created_at=datetime.now(timezone.utc),
    )
    store.RESERVATIONS[reservation.reservation_id] = reservation
    response.headers["Location"] = f"/v1/reservations/{reservation.reservation_id}"
    return in_table_zone(reservation, table)


@router.get(
    "/reservations/{reservation_id}",
    operation_id="getReservation",
    summary="Get one reservation",
    description="Returns the reservation, including one that has been cancelled.",
    response_model=Reservation,
    response_model_exclude_none=True,
    responses={**NOT_FOUND},
)
def get_reservation(reservation_id: str) -> Reservation:
    reservation = reservation_or_404(reservation_id)
    return in_table_zone(reservation, store.TABLES[reservation.table_id])


@router.patch(
    "/reservations/{reservation_id}",
    operation_id="updateReservation",
    summary="Move or retitle a reservation",
    description="Changes the window, title, or player count. The same rules and overlap check run again, ignoring this reservation.",
    response_model=Reservation,
    response_model_exclude_none=True,
    responses={**VALIDATION, **NOT_FOUND, **CONFLICT},
)
def update_reservation(reservation_id: str, body: ReservationPatch) -> Reservation:
    reservation = reservation_or_404(reservation_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise ValidationFailed(
            "Fix the fields under errors and try again.",
            errors=[{"field": "body", "message": "send at least one of starts_at, ends_at, title, or player_count"}],
        )
    if reservation.status == "cancelled":
        raise ValidationFailed(
            "Fix the fields under errors and try again.",
            errors=[{"field": "status", "message": "a cancelled reservation cannot be changed. Create a new one."}],
        )
    table = store.TABLES[reservation.table_id]
    updated = reservation.model_copy(update=changes)
    check_window(
        table,
        updated.starts_at,
        updated.ends_at,
        updated.player_count,
        ignore_id=reservation_id,
        check_past="starts_at" in changes,
    )
    store.RESERVATIONS[reservation_id] = updated
    return in_table_zone(updated, table)


@router.delete(
    "/reservations/{reservation_id}",
    operation_id="cancelReservation",
    status_code=204,
    summary="Cancel a reservation",
    description="Marks the reservation cancelled. Cancelling it again still returns 204. v1 has no login, so anyone with the id can cancel it.",
    response_class=Response,
    responses={**NOT_FOUND, 204: {"description": "The reservation is cancelled. There is no response body."}},
)
def cancel_reservation(reservation_id: str) -> Response:
    reservation = reservation_or_404(reservation_id)
    if reservation.status == "confirmed":
        store.RESERVATIONS[reservation_id] = reservation.model_copy(update={"status": "cancelled"})
    return Response(status_code=204)
