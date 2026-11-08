"""GET /v1/tables and GET /v1/tables/{table_id}. Tables are read-only in v1."""

from fastapi import APIRouter, Query

from app import store
from app.errors import NotFound, ProblemDetails
from app.models import GameTag, Table

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


def table_or_404(table_id: str) -> Table:
    table = store.TABLES.get(table_id)
    if table is None:
        raise NotFound(f"No table has id {table_id}. List tables and choose an id from that response.")
    return table
