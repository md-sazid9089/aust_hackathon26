from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging import get_logger

log = get_logger(__name__)


class ApiError(Exception):
    """Controlled, client-facing error. Rendered as the standard envelope."""

    def __init__(
        self,
        code: str,
        status: int,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message
        self.details = details or {}
        self.headers = headers or {}


class NotFound(ApiError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, 404, message)


class Conflict(ApiError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, 409, message, details)


class Forbidden(ApiError):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Not allowed") -> None:
        super().__init__(code, 403, message)


class Unauthenticated(ApiError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__("UNAUTHENTICATED", 401, message)


# constraint name → (code, message). Names must match db/models.py.
_CONSTRAINT_CODES: dict[str, tuple[str, str]] = {
    "uq_courses_owner_code_active": ("COURSE_CODE_EXISTS", "A course with this code already exists"),
    "fk_question_co_map_co_id": ("OUTCOME_IN_USE", "Outcome is referenced by a question mapping"),
    "fk_run_inputs_artefact_id": ("ARTEFACT_IN_USE", "Artefact is referenced by a run"),
}


def envelope(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status,
        headers=headers,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "request_id": request_id,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return envelope(request, exc.status, exc.code, exc.message, exc.details, exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return envelope(request, 422, "VALIDATION_ERROR", "Request validation failed", {"errors": errors})

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 401: "UNAUTHENTICATED"}.get(
            exc.status_code, "HTTP_ERROR"
        )
        return envelope(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError) -> JSONResponse:
        text = str(exc.orig) if exc.orig else str(exc)
        for name, (code, message) in _CONSTRAINT_CODES.items():
            if name in text:
                return envelope(request, 409, code, message)
        log.warning("db.integrity_error", error=text[:300])
        return envelope(request, 409, "CONFLICT", "The request conflicts with existing data")

    @app.exception_handler(OperationalError)
    async def _operational(request: Request, exc: OperationalError) -> JSONResponse:
        log.error("db.unavailable", error=str(exc)[:300])
        return envelope(request, 503, "DB_UNAVAILABLE", "Database is unavailable")

    @app.exception_handler(httpx.HTTPError)
    async def _httpx(request: Request, exc: httpx.HTTPError) -> JSONResponse:
        log.error("llm.unavailable", error=type(exc).__name__)
        return envelope(request, 503, "LLM_UNAVAILABLE", "AI provider is unavailable")

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception")
        return envelope(request, 500, "INTERNAL", "An unexpected error occurred")
