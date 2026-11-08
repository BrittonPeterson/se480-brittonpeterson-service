"""Every error leaves this service as an RFC 9457 problem-details body.

The spec (openapi.yaml, components/schemas/ProblemDetails) is the contract.
Routers raise a Problem subclass; the handlers turn it, and anything FastAPI
raises on its own, into the same shape with the same media type.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

PROBLEM_BASE = "https://se480-brittonpeterson-service.onrender.com/problems/"
PROBLEM_MEDIA_TYPE = "application/problem+json"


class ProblemDetails(BaseModel):
    """The error body. Mirrors the spec's ProblemDetails schema."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict] | None = None
    conflicts_with: dict | None = None


class Problem(Exception):
    """A problem the service knows how to describe to a caller."""

    slug = "about:blank"
    status = 500
    title = "Something went wrong"

    def __init__(self, detail: str, **extra):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class ValidationFailed(Problem):
    slug = "validation-failed"
    status = 400
    title = "Some fields in the request are not valid"


class NotFound(Problem):
    slug = "not-found"
    status = 404
    title = "Nothing was found with that id"


class Conflict(Problem):
    slug = "table-conflict"
    status = 409
    title = "The table is already held for part of that time"


def problem_response(request: Request, status: int, slug: str, title: str, detail: str, **extra) -> JSONResponse:
    type_url = slug if slug.startswith("about:") else PROBLEM_BASE + slug
    body = ProblemDetails(
        type=type_url, title=title, status=status, detail=detail, instance=request.url.path, **extra
    )
    return JSONResponse(body.model_dump(exclude_none=True), status_code=status, media_type=PROBLEM_MEDIA_TYPE)


_MESSAGES = {
    "timezone_aware": "needs an offset, for example 2026-11-07T18:00:00-06:00",
    "datetime_from_date_parsing": "needs an offset, for example 2026-11-07T18:00:00-06:00",
    "missing": "is required",
}


def _route_tree(routes):
    """FastAPI nests included routers, so the methods live on the inner routes."""
    for route in routes:
        yield route
        original = getattr(route, "original_router", None)
        if original is not None:
            yield from _route_tree(original.routes)
        nested = getattr(route, "routes", None)
        if nested:
            yield from _route_tree(nested)


def _allowed_methods(request: Request) -> str:
    """Every method any route accepts at this path.

    Starlette's own Allow header names only the first route it tried. FastAPI
    registers one route per operation, so a path with GET and POST would
    advertise GET alone.
    """
    methods: set[str] = set()
    for route in _route_tree(request.app.routes):
        route_methods = getattr(route, "methods", None)
        if not route_methods:
            continue
        match, _ = route.matches(request.scope)
        if match is not Match.NONE:
            methods |= set(route_methods)
    return ", ".join(sorted(methods))


def install(app: FastAPI) -> None:
    @app.exception_handler(Problem)
    async def handle_problem(request: Request, exc: Problem):
        return problem_response(request, exc.status, exc.slug, exc.title, exc.detail, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        errors = []
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", []) if part not in ("body", "query", "path")]
            errors.append({
                "field": ".".join(loc) or "body",
                "message": _MESSAGES.get(err.get("type"), err.get("msg", "is invalid")),
            })
        return problem_response(
            request,
            400,
            "validation-failed",
            ValidationFailed.title,
            "Fix the fields under errors and try again.",
            errors=errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            response = problem_response(
                request,
                404,
                "not-found",
                "No such path",
                "There is nothing at this path. The operations are listed at /docs.",
            )
        else:
            response = problem_response(request, exc.status_code, "about:blank", "Request not allowed", str(exc.detail))
        response.headers.update(exc.headers or {})
        if exc.status_code == 405:
            response.headers["Allow"] = _allowed_methods(request)
        return response
