from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.client import get_provider
from app.artefacts.router import router as artefacts_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.courses.router import router as courses_router
from app.db.session import get_engine, session_scope
from app.demo.router import router as demo_router
from app.demo.service import ensure_program_outcomes
from app.errors import register_error_handlers
from app.extraction.service import wait_for_extractions
from app.health.router import router as health_router
from app.logging import configure_logging, get_logger, request_id_middleware
from app.outcomes.router import router as outcomes_router
from app.runs.orchestrator import orchestrator
from app.runs.repository import RunRepo
from app.runs.router import router as runs_router

log = get_logger(__name__)

DESCRIPTION = """
**Faculty Assessment & Curriculum Copilot** — backend for the AI Build Hackathon ("AI for Academic Life").

Workflow: a faculty member creates a **course workspace** (outcomes + topics), uploads a **draft exam paper**
(and optionally past papers), confirms the extracted questions, and starts an **Exam Paper Audit** run.
The AI maps questions to outcomes and Bloom levels and confirms near-duplicates; deterministic code computes
coverage, balance, marks and fairness. Each **finding** carries a rationale and evidence; the faculty member
**accepts or dismisses** it and exports the accepted findings. AI advises; faculty decide.

Errors use one envelope: `{"error": {"code", "message", "details", "request_id"}}`.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    get_engine()
    provider = get_provider()
    log.info("startup", env=settings.env, provider=provider.name, auth_mode=settings.auth_mode, db_sqlite=settings.is_sqlite)
    try:
        async with session_scope() as db:
            swept = await RunRepo(db).sweep_stale()
            await ensure_program_outcomes(db)
        if swept:
            log.warning("startup.swept_stale_runs", count=swept)
    except Exception:  # noqa: BLE001 - DB may be down; /readyz reports it
        log.exception("startup.db_init_failed")
    yield
    await orchestrator.wait_all()
    await wait_for_extractions()
    await provider.aclose()
    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Faculty Copilot API",
        version="0.1.0",
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "Content-Disposition"],
    )
    app.middleware("http")(request_id_middleware)
    register_error_handlers(app)

    api = APIRouter(prefix="/api/v1")
    api.include_router(health_router)
    api.include_router(auth_router)
    api.include_router(courses_router)
    api.include_router(outcomes_router)
    api.include_router(artefacts_router)
    api.include_router(runs_router)
    api.include_router(demo_router)
    app.include_router(api)
    return app


app = create_app()
