from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from app.db.enums import RunModule, RunStatus
from app.db.models import Run, utcnow
from app.db.session import session_scope
from app.logging import get_logger
from app.modules.attainment.graph import run_attainment
from app.modules.base import RunContext, StageFailed, append_terminal_event
from app.modules.calibration.graph import run_calibration
from app.modules.exam_audit.graph import run_exam_audit
from app.modules.syllabus_check.graph import run_syllabus_check

log = get_logger(__name__)

Pipeline = Callable[[RunContext], Awaitable[dict[str, Any]]]

PIPELINES: dict[RunModule, Pipeline] = {
    RunModule.exam_audit: run_exam_audit,
    RunModule.attainment: run_attainment,
    RunModule.syllabus_check: run_syllabus_check,
    RunModule.calibration: run_calibration,
}


class RunOrchestrator:
    """asyncio-task runner. `enqueue` is the seam for a real queue later (D-011)."""

    def __init__(self) -> None:
        self.tasks: dict[uuid.UUID, asyncio.Task] = {}

    def enqueue(self, run_id: uuid.UUID, owner_id: uuid.UUID, course_id: uuid.UUID, module: RunModule, params: dict[str, Any]) -> asyncio.Task:
        task = asyncio.create_task(self._execute(run_id, owner_id, course_id, module, params), name=f"run:{run_id}")
        self.tasks[run_id] = task
        task.add_done_callback(lambda t: self.tasks.pop(run_id, None))
        return task

    async def wait_all(self) -> None:
        if self.tasks:
            await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)

    async def _execute(self, run_id: uuid.UUID, owner_id: uuid.UUID, course_id: uuid.UUID, module: RunModule, params: dict[str, Any]) -> None:
        ctx = RunContext(run_id=run_id, owner_id=owner_id, course_id=course_id, params=params)
        pipeline = PIPELINES.get(module)
        async with session_scope() as db:
            run = await db.get(Run, run_id)
            if run is None:
                return
            run.status = RunStatus.analyzing
            run.started_at = utcnow()
        log.info("run.started", run_id=str(run_id), module=module.value)
        status, error, summary = RunStatus.failed, None, None
        try:
            if pipeline is None:
                raise StageFailed(f"Module '{module.value}' is not implemented")
            summary = await pipeline(ctx)
            status = RunStatus.partial if ctx.warnings else RunStatus.completed
        except StageFailed as exc:
            error = str(exc)
            log.warning("run.failed", run_id=str(run_id), error=error)
        except Exception:  # noqa: BLE001 - never let a background task die silently
            error = "Analysis failed unexpectedly"
            log.exception("run.crashed", run_id=str(run_id))
        try:
            async with session_scope() as db:
                run = await db.get(Run, run_id)
                if run is not None:
                    run.status = status
                    run.error = error if status == RunStatus.failed else ("; ".join(ctx.warnings) if ctx.warnings else None)
                    run.summary = summary
                    run.model = ctx.model_used
                    run.prompt_versions = ctx.prompt_versions
                    run.progress_pct = 100
                    run.current_stage = "done"
                    run.finished_at = utcnow()
            await append_terminal_event(run_id, status.value, error or f"Run {status.value}")
            log.info(f"run.{status.value}", run_id=str(run_id))
        except Exception:  # noqa: BLE001
            log.exception("run.finalize_failed", run_id=str(run_id))


orchestrator = RunOrchestrator()
