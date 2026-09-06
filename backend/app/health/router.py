from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.ai.client import get_provider
from app.config import get_settings
from app.db.session import get_sessionmaker

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness", description="Always `{status: ok}` when the process is up.")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/readyz",
    summary="Readiness",
    description="Checks the database and reports the AI provider mode. 503 when the database is unreachable.",
)
async def readyz(request: Request) -> JSONResponse:
    settings = get_settings()
    db_ok = True
    try:
        async with get_sessionmaker()() as s:
            await s.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    provider = get_provider()
    llm = "mock" if provider.name == "mock" else ("ok" if await provider.health() else "degraded")
    body = {"db": "ok" if db_ok else "down", "llm": llm, "provider": provider.name, "env": settings.env}
    return JSONResponse(body, status_code=200 if db_ok else 503)
