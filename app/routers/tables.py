"""GET /v1/tables, one table, and its openings for a day. Tables are read-only in v1."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from app import rules, store
from app.errors import NotFound, ProblemDetails, ValidationFailed
from app.models import GameTag, Opening, Table

router = APIRouter(prefix="/v1", tags=["Tables"])

PROBLEM = {"model": ProblemDetails, "content": {"application/problem+json": {}}}


@router.get(
    "/tables",
    operation_id="listTables",
    summary="List tables in the store",
    description="Returns every table. Use the filters to narrow by seats, game, or wheelchair access.",
    response_model=list[Table],
    response_model_exclude_none=True,
    responses={400: {**PROBLEM, "description": "A field is missing, malformed, or breaks a rule."}},
)
def list_tables(
    seats_min: int | None = Query(default=None, ge=1, description="Return tables that seat at least this many players."),
    game_tag: GameTag | None = Query(default=None, description="Return tables that include this game tag."),
    wheelchair_accessible: bool | None = Query(default=None, description="When true, return only tables a wheelchair user can sit at."),
) -> list[Table]:
    tables = list(store.TABLES.values())
    if seats_min is not None:
        tables = [table for table in tables if table.seats >= seats_min]
    if game_tag is not None:
        tables = [table for table in tables if game_tag in table.game_tags]
    if wheelchair_accessible is not None:
        tables = [table for table in tables if table.wheelchair_accessible is wheelchair_accessible]
    return tables


@router.get(
    "/tables/{table_id}",
    operation_id="getTable",
    summary="Get one table",
    description="Returns the table's name, seats, tags, access, and open hours.",
    response_model=Table,
    response_model_exclude_none=True,
    responses={404: {**PROBLEM, "description": "No table has that id."}},
)
def get_table(table_id: str) -> Table:
    return table_or_404(table_id)


@router.get(
    "/tables/{table_id}/openings",
    operation_id="listTableOpenings",
    summary="Find free stretches on one table for a day",
    description=(
        "Returns the stretches of the given local day when the table is open and no confirmed reservation holds it, earliest first. "
        "Any hold of 1 to 6 hours inside a stretch passes the overlap check, as long as it starts within 14 days. "
        "Today's stretches start at the next quarter hour. A closed day returns an empty array."
    ),
    response_model=list[Opening],
    responses={
        400: {**PROBLEM, "description": "A field is missing, malformed, or breaks a rule."},
        404: {**PROBLEM, "description": "No table has that id."},
    },
)
def list_table_openings(
    table_id: str,
    day: date = Query(alias="date", description="The local day in the table's time zone, YYYY-MM-DD. Today through 14 days ahead."),
    min_length_minutes: int = Query(default=60, ge=60, le=360, description="Leave out stretches shorter than this. Defaults to 60, the shortest hold."),
) -> list[Opening]:
    table = table_or_404(table_id)
    tz = ZoneInfo(table.time_zone)
    now = datetime.now(tz)
    if day < now.date():
        raise ValidationFailed("Fix the fields under errors and try again.", errors=[{"field": "date", "message": "must be today or later"}])
    if day > (now + rules.MAX_AHEAD).date():
        raise ValidationFailed("Fix the fields under errors and try again.", errors=[{"field": "date", "message": "must be within the next 14 days"}])

    weekday = day.strftime("%A").lower()
    hours = next((row for row in table.open_hours if row.weekday == weekday), None)
    if hours is None:
        return []
    opens = datetime.combine(day, time.fromisoformat(hours.opens), tzinfo=tz)
    closes = datetime.combine(day, time.fromisoformat(hours.closes), tzinfo=tz)
    next_quarter = now.replace(second=0, microsecond=0) + timedelta(minutes=15 - now.minute % 15)
    opens = max(opens, next_quarter)

    busy = [(row.starts_at, row.ends_at) for row in store.reservations_for(table_id) if row.status == "confirmed"]
    stretches = rules.free_stretches(opens, closes, busy, timedelta(minutes=min_length_minutes))
    latest_start = now + rules.MAX_AHEAD
    return [
        Opening(starts_at=start.astimezone(tz), ends_at=end.astimezone(tz))
        for start, end in stretches
        if start <= latest_start
    ]


def table_or_404(table_id: str) -> Table:
    table = store.TABLES.get(table_id)
    if table is None:
        raise NotFound(f"No table has id {table_id}. List tables and choose an id from that response.")
    return table
