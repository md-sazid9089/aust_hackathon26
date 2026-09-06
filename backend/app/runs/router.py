from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.db.enums import (
    TERMINAL_RUN_STATUSES,
    FindingSeverity,
    FindingStatus,
    FindingType,
    Permission,
    RunModule,
    RunStatus,
)
from app.db.models import Run, RunEvent
from app.db.session import session_scope
from app.deps import DbDep, UserDep, require_permission, runs_rate_limit
from app.errors import ApiError
from app.runs.schemas import (
    AttainmentOut,
    CompareOut,
    FindingOut,
    FindingPatch,
    PrescoreOut,
    RunCreate,
    RunEventOut,
    RunOut,
    SuggestIn,
)
from app.runs.service import RunService
from app.schemas import ERROR_RESPONSES, Page

router = APIRouter(tags=["runs"])

SSE_POLL_S = 0.7
SSE_HEARTBEAT_S = 15


@router.post(
    "/courses/{course_id}/runs",
    response_model=RunOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an analysis run",
    description=(
        "Creates a run and processes it in the background. Inputs per module — exam_audit: "
        "`{draft_artefact_id, past_artefact_ids[]}` · attainment: `{marks_artefact_id, paper_artefact_id, threshold}` · "
        "syllabus_check: `{syllabus_artefact_id, compare_course_ids[]}` · calibration: `{rubric_artefact_id, answer_set_artefact_id}`. "
        "All artefacts must have status `done`. "
        "Optional `Idempotency-Key` header returns the existing run for a repeated request. Poll `GET /runs/{id}` or stream `/runs/{id}/events`."
    ),
    responses=ERROR_RESPONSES,
    dependencies=[Depends(require_permission(Permission.runs_start)), Depends(runs_rate_limit)],
)
async def create_run(
    course_id: uuid.UUID,
    data: RunCreate,
    db: DbDep,
    user: UserDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=100)] = None,
) -> RunOut:
    return await RunService(db, user).create(course_id, data, idempotency_key)


@router.get("/courses/{course_id}/runs", response_model=Page[RunOut], summary="Run history for a course", responses=ERROR_RESPONSES)
async def list_runs(
    course_id: uuid.UUID,
    db: DbDep,
    user: UserDep,
    module: Annotated[RunModule | None, Query()] = None,
    status_: Annotated[RunStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[RunOut]:
    items, total = await RunService(db, user).list_for_course(course_id, module=module, status=status_, page=page, page_size=page_size)
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/runs/compare", response_model=CompareOut, summary="Diff two finished runs of the same course (F-108)", responses=ERROR_RESPONSES)
async def compare_runs(a: uuid.UUID, b: uuid.UUID, db: DbDep, user: UserDep) -> CompareOut:
    return await RunService(db, user).compare(a, b)


@router.get("/runs/{run_id}", response_model=RunOut, summary="Run status and summary", responses=ERROR_RESPONSES)
async def get_run(run_id: uuid.UUID, db: DbDep, user: UserDep) -> RunOut:
    return await RunService(db, user).get(run_id)


@router.get("/runs/{run_id}/attainment", response_model=AttainmentOut, summary="CO/PO attainment table of an attainment run", responses=ERROR_RESPONSES)
async def get_attainment(run_id: uuid.UUID, db: DbDep, user: UserDep) -> AttainmentOut:
    return await RunService(db, user).attainment(run_id)


@router.get("/runs/{run_id}/prescores", response_model=list[PrescoreOut], summary="AI pre-scores of a calibration run", responses=ERROR_RESPONSES)
async def get_prescores(run_id: uuid.UUID, db: DbDep, user: UserDep) -> list[PrescoreOut]:
    return await RunService(db, user).prescores(run_id)


@router.post(
    "/runs/{run_id}/suggest-questions",
    response_model=list[FindingOut],
    summary="Suggest one question per uncovered CO (F-107)",
    description="Bounded suggestion for a finished exam audit; creates `suggestion` findings (idempotent per CO). Body `{co_ids?: []}`.",
    responses={**ERROR_RESPONSES, 503: {"description": "LLM_UNAVAILABLE"}},
    dependencies=[Depends(require_permission(Permission.runs_start)), Depends(runs_rate_limit)],
)
async def suggest_questions(run_id: uuid.UUID, db: DbDep, user: UserDep, data: SuggestIn | None = None) -> list[FindingOut]:
    return await RunService(db, user).suggest_questions(run_id, (data or SuggestIn()).co_ids)


@router.get(
    "/runs/{run_id}/events",
    summary="Stream run progress (SSE)",
    description=(
        "`text/event-stream`. Replays the backlog then streams live `progress` events "
        "(`{seq, stage, message, pct, level, at}`) and ends with a `done` event `{status}`. "
        "Auth via `Authorization` header or `?access_token=` (EventSource cannot set headers)."
    ),
    responses={**ERROR_RESPONSES, 200: {"content": {"text/event-stream": {}}}},
)
async def run_events(
    run_id: uuid.UUID,
    request: Request,
    db: DbDep,
    user: UserDep,
    after_seq: Annotated[int, Query(ge=-1)] = -1,
) -> EventSourceResponse:
    await RunService(db, user).get(run_id)  # ownership check (404)
    await db.commit()

    async def gen() -> AsyncIterator[dict]:
        last = after_seq
        idle = 0.0
        while True:
            if await request.is_disconnected():
                return
            async with session_scope() as s:
                events = list((await s.execute(select(RunEvent).where(RunEvent.run_id == run_id, RunEvent.seq > last).order_by(RunEvent.seq))).scalars())
                run = await s.get(Run, run_id)
            for e in events:
                last = e.seq
                idle = 0.0
                yield {"event": "progress", "id": str(e.seq), "data": RunEventOut.model_validate(e).model_dump_json()}
            if run is None or run.status in TERMINAL_RUN_STATUSES:
                yield {"event": "done", "data": json.dumps({"status": run.status.value if run else "failed"})}
                return
            await asyncio.sleep(SSE_POLL_S)
            idle += SSE_POLL_S
            if idle >= SSE_HEARTBEAT_S:
                idle = 0.0
                yield {"comment": "heartbeat"}

    return EventSourceResponse(gen())


@router.get("/runs/{run_id}/findings", response_model=list[FindingOut], summary="Findings of a run", responses=ERROR_RESPONSES)
async def list_findings(
    run_id: uuid.UUID,
    db: DbDep,
    user: UserDep,
    type_: Annotated[FindingType | None, Query(alias="type")] = None,
    status_: Annotated[FindingStatus | None, Query(alias="status")] = None,
    severity: Annotated[FindingSeverity | None, Query()] = None,
) -> list[FindingOut]:
    return await RunService(db, user).findings(run_id, type_=type_, status=status_, severity=severity)


@router.patch(
    "/findings/{finding_id}",
    response_model=FindingOut,
    summary="Accept / dismiss / reopen a finding",
    description="The faculty decision step. Only the owning faculty member may decide (admins are read-only, `403 PERMISSION_DENIED`).",
    responses=ERROR_RESPONSES,
    dependencies=[Depends(require_permission(Permission.findings_decide))],
)
async def decide_finding(finding_id: uuid.UUID, data: FindingPatch, db: DbDep, user: UserDep) -> FindingOut:
    return await RunService(db, user).decide(finding_id, data.status)


@router.get(
    "/runs/{run_id}/export",
    summary="Export findings as Markdown",
    description="Downloads a Markdown report. `include=accepted` (default) exports only faculty-accepted findings. `format=pdf` returns `503 PDF_UNAVAILABLE` on this build (clients fall back to Markdown).",
    response_class=PlainTextResponse,
    responses={**ERROR_RESPONSES, 200: {"content": {"text/markdown": {}}}, 503: {"description": "EXPORT_PDF_UNAVAILABLE"}},
)
async def export_run(
    run_id: uuid.UUID,
    db: DbDep,
    user: UserDep,
    format: Annotated[Literal["md", "pdf"], Query()] = "md",
    include: Annotated[Literal["accepted", "all"], Query()] = "accepted",
) -> Response:
    if format == "pdf":
        raise ApiError("EXPORT_PDF_UNAVAILABLE", 503, "PDF export is not available on this server; use format=md")
    md, filename = await RunService(db, user).export_markdown(run_id, include)
    return Response(content=md, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
