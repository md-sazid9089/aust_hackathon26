from __future__ import annotations

import asyncio
import uuid

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.artefacts.repository import ArtefactRepo
from app.courses.repository import CourseRepo
from app.courses.service import get_owned_course
from app.db.enums import (
    ROLE_KINDS,
    AppRole,
    ExtractionStatus,
    FindingSeverity,
    FindingStatus,
    FindingType,
    RunModule,
    RunStatus,
    TargetKind,
    UsagePurpose,
)
from app.db.models import Finding, Profile, Run, RunEvent, RunInput, utcnow
from app.errors import ApiError, Conflict, Forbidden, NotFound
from app.logging import get_logger
from app.outcomes.repository import OutcomeRepo
from app.runs.export import render_markdown
from app.runs.orchestrator import PIPELINES, orchestrator
from app.runs.repository import RunRepo
from app.runs.schemas import (
    MODULE_SCHEMAS,
    AttainmentOut,
    CalibrationInputs,
    CompareOut,
    FindingOut,
    PrescoreOut,
    RunCreate,
    RunOut,
    SyllabusCheckInputs,
    input_roles,
)

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
        course = await CourseRepo(self.db).get(run.course_id)
        if course is None:  # soft-deleted course hides its runs
            raise NotFound("RUN_NOT_FOUND", "Run not found")
        return run

    async def create(self, course_id: uuid.UUID, data: RunCreate, idempotency_key: str | None) -> RunOut:
        course = await get_owned_course(self.db, course_id, self.user)
        if data.module not in PIPELINES:
            raise ApiError("MODULE_NOT_IMPLEMENTED", 422, f"Module '{data.module.value}' is not available in this build",
                           {"available": sorted(m.value for m in PIPELINES)})
        inputs_cls, params_cls = MODULE_SCHEMAS[data.module]
        try:
            inputs = inputs_cls.model_validate(data.inputs)
            params = params_cls.model_validate(data.params)
        except ValidationError as exc:
            raise ApiError("VALIDATION_ERROR", 422, f"Invalid inputs/params for {data.module.value}",
                           {"errors": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]}) from exc
        inputs_json = inputs.model_dump(mode="json")
        if idempotency_key:
            existing = await self.repo.by_idempotency(self.user.id, idempotency_key)
            if existing is not None:
                return self._replay(existing, course.id, data.module, inputs_json)
        if data.module in (RunModule.exam_audit, RunModule.attainment) and await OutcomeRepo(self.db).count_cos(course_id) == 0:
            raise Conflict("COURSE_HAS_NO_OUTCOMES", f"Add course outcomes before running {data.module.value}")
        arepo = ArtefactRepo(self.db)
        roles = input_roles(data.module, inputs)
        for aid, role in roles:
            art = await arepo.get(aid)
            if art is None or art.course_id != course.id:
                raise NotFound("ARTEFACT_NOT_FOUND", f"Artefact {aid} not found in this course")
            if art.kind != ROLE_KINDS[role]:
                raise ApiError("VALIDATION_ERROR", 422, f"Artefact '{art.label}' is a {art.kind.value}, expected {ROLE_KINDS[role].value}")
            if art.status != ExtractionStatus.done:
                raise Conflict("ARTEFACT_NOT_READY", f"Artefact '{art.label}' is {art.status.value}; confirm extraction first")
        if isinstance(inputs, SyllabusCheckInputs):
            crepo = CourseRepo(self.db)
            for cid in inputs.compare_course_ids:
                other = await crepo.get(cid)
                if other is None or other.owner_id != self.user.id or other.id == course.id:
                    raise NotFound("COURSE_NOT_FOUND", f"Comparison course {cid} not found")
        if isinstance(inputs, CalibrationInputs):
            await self._check_scores_within_rubric(arepo, inputs)
        run_params = params.model_dump()
        if hasattr(inputs, "threshold"):
            run_params["threshold"] = inputs.threshold
        run = Run(
            course_id=course.id, owner_id=self.user.id, module=data.module, status=RunStatus.queued,
            inputs=inputs_json, params=run_params, idempotency_key=idempotency_key,
        )
        try:
            self.db.add(run)
            await self.db.flush()
            self.db.add_all(RunInput(run_id=run.id, artefact_id=aid, role=role) for aid, role in roles)
            self.db.add(RunEvent(run_id=run.id, seq=0, stage="queued", message="Run queued", pct=0))
            await self.db.commit()  # background task needs to see the row
        except IntegrityError:
            await self.db.rollback()
            if not idempotency_key:
                raise
            # A concurrent request with the same Idempotency-Key won the race; wait for its commit and replay it.
            for _ in range(20):
                existing = await self.repo.by_idempotency(self.user.id, idempotency_key)
                if existing is not None:
                    return self._replay(existing, course.id, data.module, inputs_json)
                await asyncio.sleep(0.05)
            raise
        orchestrator.enqueue(run.id, self.user.id, course.id, run.module, run.params)
        log.info("run.created", run_id=str(run.id), module=run.module.value)
        return RunOut.model_validate(run)

    @staticmethod
    def _replay(existing: Run, course_id: uuid.UUID, module: RunModule, inputs_json: dict) -> RunOut:
        if existing.course_id != course_id or existing.module != module or existing.inputs != inputs_json:
            raise Conflict("IDEMPOTENCY_KEY_REUSED", "Idempotency-Key was already used with a different request")
        return RunOut.model_validate(existing)

    async def _check_scores_within_rubric(self, arepo: ArtefactRepo, inputs: CalibrationInputs) -> None:
        """`grader_scores.score ≤ rubric max_score` cannot be a DB CHECK (separate artefacts) → 409 SCORES_EXCEED_RUBRIC."""
        maxes = {c.code: float(c.max_score) for c in await arepo.rubric(inputs.rubric_artefact_id)}
        if not maxes:
            raise Conflict("ARTEFACT_NOT_READY", "Rubric has no criteria; confirm the extraction first")
        bad: list[dict] = []
        unknown: set[str] = set()
        graders: set[str] = set()
        for a in await arepo.answers(inputs.answer_set_artefact_id):
            for g in a.grader_scores or []:
                graders.add(g["grader_label"])
                mx = maxes.get(g["criterion_code"])
                if mx is None:
                    unknown.add(g["criterion_code"])
                elif float(g["score"]) > mx:
                    bad.append({"student_anon_id": a.student_anon_id, "criterion_code": g["criterion_code"], "score": g["score"], "max_score": mx})
        if bad:
            raise Conflict("SCORES_EXCEED_RUBRIC", "Some grader scores exceed the rubric maximum", {"violations": bad[:20]})
        if unknown:
            raise Conflict("SCORES_EXCEED_RUBRIC", "Grader scores reference criteria not in the rubric", {"unknown_criteria": sorted(unknown)})
        if len(graders) < 2:
            raise Conflict("ARTEFACT_NOT_READY", "Calibration needs scores from at least two graders")

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
        run = await self.repo.get(finding.run_id)
        if run is None or await CourseRepo(self.db).get(run.course_id) is None:
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
        return md, f"{run.module.value.replace('_', '-')}-{safe_code}-{str(run.id)[:8]}.md"

    # --- Tier-1 result views -----------------------------------------------------------
    async def attainment(self, run_id: uuid.UUID) -> AttainmentOut:
        run = await self._owned_run(run_id)
        if run.module != RunModule.attainment:
            raise ApiError("VALIDATION_ERROR", 422, "Not an attainment run")
        if run.status not in (RunStatus.completed, RunStatus.partial) or not run.summary:
            raise Conflict("RUN_NOT_COMPLETED", "Run has not finished")
        s = run.summary
        return AttainmentOut(threshold=s.get("threshold", 0.6), cos=s.get("cos", []), pos=s.get("pos", []))

    async def prescores(self, run_id: uuid.UUID) -> list[PrescoreOut]:
        run = await self._owned_run(run_id)
        if run.module != RunModule.calibration:
            raise ApiError("VALIDATION_ERROR", 422, "Not a calibration run")
        if run.status not in (RunStatus.completed, RunStatus.partial) or not run.summary:
            raise Conflict("RUN_NOT_COMPLETED", "Run has not finished")
        return [PrescoreOut.model_validate(p) for p in run.summary.get("prescores", [])]

    async def compare(self, a_id: uuid.UUID, b_id: uuid.UUID) -> CompareOut:
        """F-108: diff two exam-audit runs of the same course. Findings match on (type, target_label)."""
        a, b = await self._owned_run(a_id), await self._owned_run(b_id)
        if a.course_id != b.course_id:
            raise ApiError("VALIDATION_ERROR", 422, "Runs belong to different courses")
        if a.module != b.module:
            raise ApiError("VALIDATION_ERROR", 422, "Runs are of different modules")
        for r in (a, b):
            if r.status not in (RunStatus.completed, RunStatus.partial):
                raise Conflict("RUN_NOT_COMPLETED", f"Run {r.id} has not finished")
        fa = await self.repo.findings(a.id, type_=None, status=None, severity=None)
        fb = await self.repo.findings(b.id, type_=None, status=None, severity=None)
        key = lambda f: (f.type.value, (f.target_label or f.title).lower())  # noqa: E731
        ia = {key(f): f for f in fa if f.type != FindingType.suggestion}
        ib = {key(f): f for f in fb if f.type != FindingType.suggestion}
        return CompareOut(
            resolved=[FindingOut.model_validate(f) for k, f in ia.items() if k not in ib],
            new=[FindingOut.model_validate(f) for k, f in ib.items() if k not in ia],
            persisting=[{"a": FindingOut.model_validate(ia[k]), "b": FindingOut.model_validate(ib[k])} for k in ia if k in ib],
        )

    async def suggest_questions(self, run_id: uuid.UUID, co_ids: list[uuid.UUID]) -> list[FindingOut]:
        """F-107: bounded question suggestion for uncovered COs of a finished exam audit; idempotent per CO."""
        from app.ai.client import CallContext, structured_call
        from app.modules import tier1_prompts as P

        run = await self._owned_run(run_id)
        if run.owner_id != self.user.id:
            raise Forbidden("FORBIDDEN", "Only the owning faculty member can request suggestions")
        if run.module != RunModule.exam_audit:
            raise ApiError("VALIDATION_ERROR", 422, "Suggestions are only available for exam audits")
        if run.status not in (RunStatus.completed, RunStatus.partial):
            raise Conflict("RUN_NOT_COMPLETED", "Run has not finished")
        course = await get_owned_course(self.db, run.course_id, self.user)
        gaps = await self.repo.findings(run.id, type_=FindingType.coverage_gap, status=None, severity=None)
        existing = {f.target_label for f in await self.repo.findings(run.id, type_=FindingType.suggestion, status=None, severity=None)}
        wanted = {g.target_id for g in gaps if g.target_id and (not co_ids or g.target_id in co_ids)}
        cos = [c for c in await OutcomeRepo(self.db).course_outcomes(course.id) if c.id in wanted and c.code not in existing]
        if not cos:
            return [FindingOut.model_validate(f) for f in await self.repo.findings(run.id, type_=FindingType.suggestion, status=None, severity=None)]
        snapshot = run.context_snapshot or {}
        style = "\n".join(f"- {q['number']} [{q['marks']}] {q['text'][:160]}" for q in snapshot.get("draft_questions", [])[:8]) or "- (none)"
        cos_txt = "\n".join(f"- {c.code} ({c.bloom_level.value if c.bloom_level else 'unspecified'}): {c.text}" for c in cos)
        res = await structured_call(
            purpose="suggest_questions", usage_purpose=UsagePurpose.suggestion, system=P.SUGGEST_SYSTEM,
            user=P.SUGGEST_USER.format(course_code=course.code, course_title=course.title, cos=cos_txt, questions=style),
            schema=P.SuggestOut, ctx=CallContext(self.user.id, run.id), db=self.db,
            context={"cos": [{"code": c.code, "text": c.text, "bloom_level": c.bloom_level.value if c.bloom_level else None} for c in cos]},
        )
        if res.value is None:
            raise ApiError("LLM_UNAVAILABLE", 503, f"Question suggestion unavailable ({res.error})")
        by_code = {c.code: c for c in cos}
        for it in res.value.items:  # type: ignore[union-attr]
            c = by_code.get(it.co_code)
            if c is None:
                continue
            self.db.add(Finding(
                run_id=run.id, owner_id=run.owner_id, type=FindingType.suggestion, severity=FindingSeverity.info,
                title=f"Suggested question for {c.code} ({it.marks:g} marks, {it.bloom_level})",
                rationale=it.rationale, evidence_snippet=it.question, target_kind=TargetKind.course_outcome, target_id=c.id, target_label=c.code,
                payload={"question": it.question, "marks": it.marks, "bloom_level": it.bloom_level},
                provenance={"model": res.model, "prompt": "SUGGEST_QUESTIONS", "version": P.PROMPT_VERSIONS["SUGGEST_QUESTIONS"]},
            ))
        await self.db.flush()
        log.info("suggestions.generated", run_id=str(run.id), count=len(res.value.items))  # type: ignore[union-attr]
        return [FindingOut.model_validate(f) for f in await self.repo.findings(run.id, type_=FindingType.suggestion, status=None, severity=None)]
