"""GET /v1/tables, one table, and its openings for a day. Tables are read-only in v1."""

from datetime import date, datetime, timedelta
from typing import Annotated
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
    seats_min: Annotated[
        int | None,
        Query(ge=1, description="Return tables that seat at least this many players."),
    ] = None,
    game_tag: Annotated[
        GameTag | None, Query(description="Return tables that include this game tag.")
    ] = None,
    wheelchair_accessible: Annotated[
        bool | None,
        Query(description="When true, return only tables a wheelchair user can sit at."),
    ] = None,
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
        "Returns the stretches of the given local day when the table is open and no confirmed "
        "reservation holds it, earliest first. Any hold of 1 to 6 hours inside a stretch passes "
        "the overlap check, as long as it starts within 14 days. Today's stretches start at the "
        "next quarter hour. A closed day returns an empty array."
    ),
    response_model=list[Opening],
    responses={
        400: {**PROBLEM, "description": "A field is missing, malformed, or breaks a rule."},
        404: {**PROBLEM, "description": "No table has that id."},
    },
)
def list_table_openings(
    table_id: str,
    day: Annotated[
        date,
        Query(
            alias="date",
            description=(
                "The local day in the table's time zone, YYYY-MM-DD. Today through 14 days ahead."
            ),
        ),
    ],
    min_length_minutes: Annotated[
        int,
        Query(
            ge=60,
            le=360,
            description="Leave out stretches shorter than this. Defaults to 60, the shortest hold.",
        ),
    ] = 60,
) -> list[Opening]:
    table = table_or_404(table_id)
    now = datetime.now(ZoneInfo(table.time_zone))
    errors = rules.openings_day_errors(day, now)
    if errors:
        raise ValidationFailed("Fix the fields under errors and try again.", errors=errors)

    busy = [
        (row.starts_at, row.ends_at)
        for row in store.reservations_for(table_id)
        if row.status == "confirmed"
    ]
    stretches = rules.openings(
        day, now, table.time_zone, table.open_hours, busy, timedelta(minutes=min_length_minutes)
    )
    return [Opening(starts_at=start, ends_at=end) for start, end in stretches]


def table_or_404(table_id: str) -> Table:
    table = store.TABLES.get(table_id)
    if table is None:
        raise NotFound(
            f"No table has id {table_id}. List tables and choose an id from that response."
        )
    return table
