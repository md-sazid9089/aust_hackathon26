from __future__ import annotations

import uuid

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.artefacts.repository import ArtefactRepo
from app.courses.service import get_owned_course
from app.db.enums import (
    IMPLEMENTED_MODULES,
    AppRole,
    ArtefactKind,
    ExtractionStatus,
    FindingSeverity,
    FindingStatus,
    FindingType,
    RunModule,
    RunStatus,
)
from app.db.models import Finding, Profile, Run, RunEvent, RunInput, utcnow
from app.errors import ApiError, Conflict, Forbidden, NotFound
from app.logging import get_logger
from app.outcomes.repository import OutcomeRepo
from app.runs.export import render_markdown
from app.runs.orchestrator import orchestrator
from app.runs.repository import RunRepo
from app.runs.schemas import ExamAuditInputs, ExamAuditParams, FindingOut, RunCreate, RunOut

log = get_logger(__name__)


class RunService:
    def __init__(self, db: AsyncSession, user: Profile) -> None:
        self.db = db
        self.user = user
        self.repo = RunRepo(db)

    async def _owned_run(self, run_id: uuid.UUID) -> Run:
        run = await self.repo.get(run_id)
        if run is None or (run.owner_id != self.user.id and self.user.role != AppRole.admin):
            raise NotFound("RUN_NOT_FOUND", "Run not found")
        return run

    async def create(self, course_id: uuid.UUID, data: RunCreate, idempotency_key: str | None) -> RunOut:
        course = await get_owned_course(self.db, course_id, self.user)
        if idempotency_key:
            existing = await self.repo.by_idempotency(self.user.id, idempotency_key)
            if existing is not None:
                return RunOut.model_validate(existing)
        if data.module not in IMPLEMENTED_MODULES:
            raise ApiError("MODULE_NOT_IMPLEMENTED", 422, f"Module '{data.module.value}' is not available in this build",
                           {"available": sorted(m.value for m in IMPLEMENTED_MODULES)})
        try:
            inputs = ExamAuditInputs.model_validate(data.inputs)
            params = ExamAuditParams.model_validate(data.params)
        except ValidationError as exc:
            raise ApiError("VALIDATION_ERROR", 422, "Invalid inputs/params for exam_audit",
                           {"errors": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]}) from exc
        if await OutcomeRepo(self.db).count_cos(course_id) == 0:
            raise Conflict("COURSE_HAS_NO_OUTCOMES", "Add course outcomes before running an exam audit")
        arepo = ArtefactRepo(self.db)
        roles: list[tuple[uuid.UUID, str]] = [(inputs.draft_artefact_id, "draft")] + [(a, "past") for a in inputs.past_artefact_ids]
        for aid, _role in roles:
            art = await arepo.get(aid)
            if art is None or art.course_id != course.id:
                raise NotFound("ARTEFACT_NOT_FOUND", f"Artefact {aid} not found in this course")
            if art.kind != ArtefactKind.question_paper:
                raise ApiError("VALIDATION_ERROR", 422, f"Artefact {aid} is not a question paper")
            if art.status != ExtractionStatus.done:
                raise Conflict("ARTEFACT_NOT_READY", f"Artefact '{art.label}' is {art.status.value}; confirm extraction first")
        run = Run(
            course_id=course.id, owner_id=self.user.id, module=data.module, status=RunStatus.queued,
            inputs=inputs.model_dump(mode="json"), params=params.model_dump(), idempotency_key=idempotency_key,
        )
        self.db.add(run)
        await self.db.flush()
        self.db.add_all(RunInput(run_id=run.id, artefact_id=aid, role=role) for aid, role in roles)
        self.db.add(RunEvent(run_id=run.id, seq=0, stage="queued", message="Run queued", pct=0))
        await self.db.commit()  # background task needs to see the row
        orchestrator.enqueue(run.id, self.user.id, course.id, run.module, run.params)
        log.info("run.created", run_id=str(run.id), module=run.module.value)
        return RunOut.model_validate(run)

    async def list_for_course(self, course_id: uuid.UUID, *, module: RunModule | None, status: RunStatus | None, page: int, page_size: int) -> tuple[list[RunOut], int]:
        await get_owned_course(self.db, course_id, self.user)
        rows, total = await self.repo.list_for_course(course_id, module=module, status=status, offset=(page - 1) * page_size, limit=page_size)
        return [RunOut.model_validate(r) for r in rows], total

    async def get(self, run_id: uuid.UUID) -> RunOut:
        return RunOut.model_validate(await self._owned_run(run_id))

    async def events(self, run_id: uuid.UUID, after_seq: int = -1) -> list[RunEvent]:
        run = await self._owned_run(run_id)
        return await self.repo.events(run.id, after_seq)

    async def findings(self, run_id: uuid.UUID, *, type_: FindingType | None, status: FindingStatus | None, severity: FindingSeverity | None) -> list[FindingOut]:
        run = await self._owned_run(run_id)
        return [FindingOut.model_validate(f) for f in await self.repo.findings(run.id, type_=type_, status=status, severity=severity)]

    async def decide(self, finding_id: uuid.UUID, status: FindingStatus) -> FindingOut:
        finding = await self.repo.finding(finding_id)
        if finding is None or (finding.owner_id != self.user.id and self.user.role != AppRole.admin):
            raise NotFound("FINDING_NOT_FOUND", "Finding not found")
        if finding.owner_id != self.user.id:
            raise Forbidden("FORBIDDEN", "Only the owning faculty member can decide on a finding")
        finding.status = status
        if status == FindingStatus.open:
            finding.decided_by, finding.decided_at = None, None
        else:
            finding.decided_by, finding.decided_at = self.user.id, utcnow()
        await self.db.flush()
        log.info("finding.decided", finding_id=str(finding.id), status=status.value)
        return FindingOut.model_validate(finding)

    async def export_markdown(self, run_id: uuid.UUID, include: str) -> tuple[str, str]:
        run = await self._owned_run(run_id)
        if run.status not in (RunStatus.completed, RunStatus.partial):
            raise Conflict("RUN_NOT_COMPLETED", "Run has not finished")
        course = await get_owned_course(self.db, run.course_id, self.user)
        status = FindingStatus.accepted if include == "accepted" else None
        findings: list[Finding] = await self.repo.findings(run.id, type_=None, status=status, severity=None)
        md = render_markdown(run, findings, course_code=course.code, course_title=course.title, include=include)
        log.info("export.generated", run_id=str(run.id), include=include)
        safe_code = "".join(ch for ch in course.code if ch.isalnum() or ch in "-_") or "course"
        return md, f"exam-audit-{safe_code}-{str(run.id)[:8]}.md"
