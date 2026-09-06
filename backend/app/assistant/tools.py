"""Tool registry for the assistant. Every tool delegates to the existing service layer, so ownership,
validation and permission rules are identical to the REST API."""

from __future__ import annotations

import asyncio
import io
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.artefacts.service import ArtefactService
from app.courses.schemas import CourseCreate, CourseUpdate
from app.courses.service import CourseService
from app.db.enums import ArtefactKind, ExtractionStatus, FindingStatus, FindingType, Permission, RunModule, RunStatus
from app.db.models import Profile
from app.demo.service import seed_demo
from app.deps import has_permission
from app.errors import ApiError
from app.extraction.service import extraction_task
from app.outcomes.schemas import CourseOutcomeIn, TopicIn
from app.outcomes.service import OutcomeService
from app.runs.orchestrator import orchestrator
from app.runs.schemas import RunCreate
from app.runs.service import RunService

WAIT_EXTRACTION_S = 90.0
WAIT_RUN_S = 120.0


@dataclass
class Attachment:
    filename: str
    data: bytes


@dataclass
class ToolEnv:
    db: AsyncSession
    user: Profile
    attachment: Attachment | None = None
    current_course_id: uuid.UUID | None = None
    attachment_used: bool = False


@dataclass
class ToolResult:
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    navigate: str | None = None
    ok: bool = True


class ToolError(Exception):
    pass


ToolFn = Callable[[ToolEnv, Any], Awaitable[ToolResult]]


@dataclass
class ToolSpec:
    name: str
    description: str
    args: type[BaseModel]
    fn: ToolFn
    permission: Permission | None = None


TOOLS: dict[str, ToolSpec] = {}


def tool(name: str, description: str, args: type[BaseModel], permission: Permission | None = None):
    def deco(fn: ToolFn) -> ToolFn:
        TOOLS[name] = ToolSpec(name=name, description=description, args=args, fn=fn, permission=permission)
        return fn

    return deco


def catalogue() -> str:
    lines = []
    for spec in TOOLS.values():
        props = spec.args.model_json_schema().get("properties", {})
        params = ", ".join(f"{k}{'?' if 'default' in v or 'anyOf' in v else ''}" for k, v in props.items()) or "(none)"
        lines.append(f"- {spec.name} — {params} — {spec.description}")
    return "\n".join(lines)


async def execute(env: ToolEnv, name: str, raw_args: dict[str, Any]) -> ToolResult:
    spec = TOOLS.get(name)
    if spec is None:
        return ToolResult(summary=f"Unknown tool '{name}'", ok=False)
    if spec.permission and not has_permission(env.user, spec.permission):
        return ToolResult(summary=f"Your role does not allow '{name}'", ok=False)
    try:
        args = spec.args.model_validate(raw_args or {})
    except ValidationError as exc:
        return ToolResult(summary=f"Invalid arguments for {name}: " + "; ".join(e["msg"] for e in exc.errors()), ok=False)
    try:
        return await spec.fn(env, args)
    except ApiError as exc:
        return ToolResult(summary=f"{exc.code}: {exc.message}", data={"details": exc.details}, ok=False)
    except (ToolError, ValidationError) as exc:
        return ToolResult(summary=str(exc)[:500], ok=False)
    except TimeoutError:
        return ToolResult(summary="Timed out waiting for background work; check the run/artefact page later", ok=False)


# --- helpers -----------------------------------------------------------------
def _uuid(value: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value)) if value else None
    except ValueError:
        return None


async def _resolve_course(env: ToolEnv, ref: str | None) -> uuid.UUID:
    """Accept a course id or code; fall back to the page's current course."""
    if ref:
        cid = _uuid(ref)
        if cid:
            return cid
        rows, _ = await CourseService(env.db, env.user).list(q=ref, page=1, page_size=5, sort="created_at:desc")
        exact = [c for c in rows if c.code.lower() == " ".join(ref.upper().split()).lower()]
        if len(exact) == 1:
            return exact[0].id
        if len(rows) == 1:
            return rows[0].id
        raise ToolError(f"Could not identify course '{ref}'" + (f" (matches: {', '.join(c.code for c in rows)})" if rows else ""))
    if env.current_course_id:
        return env.current_course_id
    raise ToolError("No course specified")


async def _release_locks(env: ToolEnv) -> None:
    # SQLite is single-writer: commit the request transaction before awaiting a background task.
    await env.db.commit()


async def _await_task(task: asyncio.Task | None, timeout: float) -> None:
    if task is not None and not task.done():
        await asyncio.wait_for(asyncio.shield(task), timeout)


def _artefact_brief(a) -> dict[str, Any]:  # noqa: ANN001
    return {
        "id": str(a.id), "kind": a.kind.value, "label": a.label, "status": a.status.value, "year": a.year,
        "error": a.error, "counts": a.counts.model_dump() if a.counts else None,
    }


def _finding_brief(f) -> dict[str, Any]:  # noqa: ANN001
    return {
        "id": str(f.id), "type": f.type.value, "severity": f.severity.value, "status": f.status.value,
        "title": f.title, "target": f.target_label, "rationale": f.rationale[:300],
    }


def _run_brief(r) -> dict[str, Any]:  # noqa: ANN001
    return {
        "id": str(r.id), "module": r.module.value, "status": r.status.value, "progress_pct": r.progress_pct,
        "error": r.error, "created_at": r.created_at.isoformat(), "summary": _compact_summary(r.summary),
    }


def _compact_summary(summary: dict[str, Any] | None) -> dict[str, Any] | None:
    if not summary:
        return None
    keep = {k: v for k, v in summary.items() if k in ("questions", "past_questions", "marks_total", "coverage", "bloom", "duplicates", "counts", "findings")}
    return keep or {k: summary[k] for k in list(summary)[:6]}


# --- courses -------------------------------------------------------------------
class NoArgs(BaseModel):
    pass


class CourseRef(BaseModel):
    course: str | None = Field(None, description="course id or course code; defaults to the current page's course")


@tool("list_courses", "List the user's courses with counts.", NoArgs)
async def list_courses(env: ToolEnv, _: NoArgs) -> ToolResult:
    rows, total = await CourseService(env.db, env.user).list(q=None, page=1, page_size=100, sort="created_at:desc")
    items = [{"id": str(c.id), "code": c.code, "title": c.title, "term": c.term, "is_demo": c.is_demo} for c in rows]
    return ToolResult(summary=f"{total} course(s)", data={"courses": items}, navigate="/courses")


class CreateCourseArgs(BaseModel):
    code: str
    title: str
    term: str | None = None
    description: str | None = None


@tool("create_course", "Create a new course workspace.", CreateCourseArgs, Permission.courses_write)
async def create_course(env: ToolEnv, a: CreateCourseArgs) -> ToolResult:
    c = await CourseService(env.db, env.user).create(CourseCreate(**a.model_dump()))
    return ToolResult(summary=f"Created course {c.code} — {c.title}", data={"course": {"id": str(c.id), "code": c.code, "title": c.title}}, navigate=f"/courses/{c.id}")


class UpdateCourseArgs(CourseRef):
    code: str | None = None
    title: str | None = None
    term: str | None = None
    description: str | None = None


@tool("update_course", "Rename a course or change its term/description.", UpdateCourseArgs, Permission.courses_write)
async def update_course(env: ToolEnv, a: UpdateCourseArgs) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    c = await CourseService(env.db, env.user).update(cid, CourseUpdate(**a.model_dump(exclude={"course"}, exclude_none=True)))
    return ToolResult(summary=f"Updated course {c.code}", data={"course": {"id": str(c.id), "code": c.code, "title": c.title}}, navigate=f"/courses/{c.id}")


@tool("delete_course", "Delete (archive) a course. Only when the user explicitly asks.", CourseRef, Permission.courses_write)
async def delete_course(env: ToolEnv, a: CourseRef) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    await CourseService(env.db, env.user).delete(cid)
    return ToolResult(summary="Course deleted", navigate="/courses")


@tool("course_overview", "Outcomes, topics, artefacts and recent runs of a course.", CourseRef)
async def course_overview(env: ToolEnv, a: CourseRef) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    course = await CourseService(env.db, env.user).get(cid)
    osvc = OutcomeService(env.db, env.user)
    cos = await osvc.list_outcomes(cid)
    topics = await osvc.topics(cid)
    arts = await ArtefactService(env.db, env.user).list(cid, kind=None, status=None)
    runs, _ = await RunService(env.db, env.user).list_for_course(cid, module=None, status=None, page=1, page_size=5)
    data = {
        "course": {"id": str(course.id), "code": course.code, "title": course.title, "term": course.term},
        "outcomes": [{"id": str(c.id), "code": c.code, "text": c.text, "bloom_level": c.bloom_level} for c in cos],
        "topics": [{"code": t.code, "title": t.title} for t in topics],
        "artefacts": [_artefact_brief(x) for x in arts],
        "recent_runs": [_run_brief(r) for r in runs],
    }
    return ToolResult(summary=f"{course.code}: {len(cos)} COs, {len(topics)} topics, {len(arts)} artefacts, {len(runs)} recent runs", data=data, navigate=f"/courses/{cid}")


# --- outcomes / topics ---------------------------------------------------------
class OutcomeItem(BaseModel):
    code: str
    text: str
    bloom_level: str | None = None


class SetOutcomesArgs(CourseRef):
    items: list[OutcomeItem]
    mode: Literal["append", "replace"] = "append"


@tool("set_outcomes", "Add course outcomes (mode=append, default) or replace the whole list (mode=replace).", SetOutcomesArgs, Permission.courses_write)
async def set_outcomes(env: ToolEnv, a: SetOutcomesArgs) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    svc = OutcomeService(env.db, env.user)
    items: list[CourseOutcomeIn] = []
    if a.mode == "append":
        items = [CourseOutcomeIn(id=c.id, code=c.code, text=c.text, bloom_level=c.bloom_level, weight=c.weight) for c in await svc.list_outcomes(cid)]
    codes = {i.code for i in items}
    for it in a.items:
        if " ".join(it.code.upper().split()) in codes:
            continue
        items.append(CourseOutcomeIn(code=it.code, text=it.text, bloom_level=it.bloom_level))  # type: ignore[arg-type]
    rows = await svc.replace_outcomes(cid, items)
    return ToolResult(summary=f"Course now has {len(rows)} outcomes", data={"outcomes": [{"id": str(c.id), "code": c.code, "text": c.text} for c in rows]}, navigate=f"/courses/{cid}")


class TopicItem(BaseModel):
    code: str
    title: str


class SetTopicsArgs(CourseRef):
    items: list[TopicItem]
    mode: Literal["append", "replace"] = "append"


@tool("set_topics", "Add syllabus topics (append) or replace them.", SetTopicsArgs, Permission.courses_write)
async def set_topics(env: ToolEnv, a: SetTopicsArgs) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    svc = OutcomeService(env.db, env.user)
    items: list[TopicIn] = []
    if a.mode == "append":
        items = [TopicIn(id=t.id, code=t.code, title=t.title) for t in await svc.topics(cid)]
    codes = {i.code for i in items}
    items += [TopicIn(code=t.code, title=t.title) for t in a.items if " ".join(t.code.upper().split()) not in codes]
    rows = await svc.replace_topics(cid, items)
    return ToolResult(summary=f"Course now has {len(rows)} topics", data={"topics": [{"code": t.code, "title": t.title} for t in rows]}, navigate=f"/courses/{cid}")


# --- artefacts -----------------------------------------------------------------
class UploadArgs(CourseRef):
    kind: ArtefactKind = ArtefactKind.question_paper
    label: str | None = Field(None, description="defaults to the file name")
    year: int | None = None
    declared_total_marks: float | None = None


async def _upload_attachment(env: ToolEnv, a: UploadArgs):  # noqa: ANN202
    if env.attachment is None:
        raise ToolError("No file is attached to this message")
    if env.attachment_used:
        raise ToolError("The attached file was already uploaded in this turn")
    cid = await _resolve_course(env, a.course)
    upload = UploadFile(io.BytesIO(env.attachment.data), filename=env.attachment.filename)
    label = (a.label or env.attachment.filename.rsplit(".", 1)[0] or "Upload")[:200]
    out = await ArtefactService(env.db, env.user).create(
        cid, kind=a.kind, label=label, year=a.year, term=None, declared_total_marks=a.declared_total_marks, file=upload, text=None,
    )
    env.attachment_used = True
    await _await_task(extraction_task(out.id), WAIT_EXTRACTION_S)
    env.db.expunge_all()
    return cid, await ArtefactService(env.db, env.user).get(out.id)


@tool("upload_attachment", "Upload the file attached to this message as an artefact of a course and wait for extraction.", UploadArgs, Permission.artefacts_write)
async def upload_attachment(env: ToolEnv, a: UploadArgs) -> ToolResult:
    cid, art = await _upload_attachment(env, a)
    return ToolResult(summary=f"Uploaded '{art.label}' ({art.kind.value}); extraction {art.status.value}", data={"artefact": _artefact_brief(art)}, navigate=f"/courses/{cid}", ok=art.status != ExtractionStatus.failed)


class TextArtefactArgs(CourseRef):
    kind: ArtefactKind
    label: str
    text: str


@tool("add_text_artefact", "Create an artefact from pasted text (≥ 20 chars) and wait for extraction.", TextArtefactArgs, Permission.artefacts_write)
async def add_text_artefact(env: ToolEnv, a: TextArtefactArgs) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    out = await ArtefactService(env.db, env.user).create(cid, kind=a.kind, label=a.label, year=None, term=None, declared_total_marks=None, file=None, text=a.text)
    await _await_task(extraction_task(out.id), WAIT_EXTRACTION_S)
    env.db.expunge_all()
    art = await ArtefactService(env.db, env.user).get(out.id)
    return ToolResult(summary=f"Added '{art.label}' ({art.kind.value}); extraction {art.status.value}", data={"artefact": _artefact_brief(art)}, navigate=f"/courses/{cid}")


class ArtefactRef(BaseModel):
    artefact_id: str


@tool("delete_artefact", "Delete an artefact. Only when the user explicitly asks.", ArtefactRef, Permission.artefacts_write)
async def delete_artefact(env: ToolEnv, a: ArtefactRef) -> ToolResult:
    aid = _uuid(a.artefact_id)
    if not aid:
        raise ToolError("artefact_id must be a uuid")
    await ArtefactService(env.db, env.user).delete(aid)
    return ToolResult(summary="Artefact deleted")


@tool("get_questions", "Extracted questions of a question paper (number, marks, Bloom level, mapped COs).", ArtefactRef)
async def get_questions(env: ToolEnv, a: ArtefactRef) -> ToolResult:
    aid = _uuid(a.artefact_id)
    if not aid:
        raise ToolError("artefact_id must be a uuid")
    svc = ArtefactService(env.db, env.user)
    art = await svc.get(aid)
    qs = await svc.questions(aid)
    co_codes = {c.id: c.code for c in await OutcomeService(env.db, env.user).list_outcomes(art.course_id)}
    items = [{"number": q.number, "marks": q.marks, "bloom_level": q.bloom_level, "cos": [co_codes.get(c, "?") for c in q.co_ids], "text": q.text[:240]} for q in qs]
    return ToolResult(summary=f"{len(items)} questions, {sum(q.marks or 0 for q in qs):g} marks in total", data={"artefact": _artefact_brief(art), "questions": items})


# --- runs & findings -----------------------------------------------------------
class RunAuditArgs(CourseRef):
    draft_artefact_id: str | None = Field(None, description="defaults to the most recent extracted question paper")
    past_artefact_ids: list[str] | None = Field(None, description="defaults to all other extracted question papers")
    wait: bool = True


async def _run_exam_audit(env: ToolEnv, cid: uuid.UUID, draft_id: uuid.UUID | None, past_ids: list[uuid.UUID] | None, wait: bool) -> ToolResult:
    papers = await ArtefactService(env.db, env.user).list(cid, kind=ArtefactKind.question_paper, status=ExtractionStatus.done)
    if draft_id is None:
        if not papers:
            raise ToolError("The course has no extracted question paper to audit — upload one first")
        draft_id = papers[0].id
    if past_ids is None:
        past_ids = [p.id for p in papers if p.id != draft_id][:10]
    svc = RunService(env.db, env.user)
    run = await svc.create(cid, RunCreate(module=RunModule.exam_audit, inputs={"draft_artefact_id": str(draft_id), "past_artefact_ids": [str(p) for p in past_ids]}), None)
    nav = f"/courses/{cid}/exam-audit/{run.id}"
    if not wait:
        return ToolResult(summary=f"Exam audit started (run {run.id})", data={"run": _run_brief(run)}, navigate=nav)
    await _await_task(orchestrator.tasks.get(run.id), WAIT_RUN_S)
    env.db.expunge_all()
    run = await svc.get(run.id)
    findings = await svc.findings(run.id, type_=None, status=None, severity=None)
    by_sev: dict[str, int] = {}
    for f in findings:
        by_sev[f.severity.value] = by_sev.get(f.severity.value, 0) + 1
    return ToolResult(
        summary=f"Exam audit {run.status.value}: {len(findings)} findings ({', '.join(f'{v} {k}' for k, v in by_sev.items()) or 'none'})",
        data={"run": _run_brief(run), "findings": [_finding_brief(f) for f in findings[:25]], "past_papers_compared": len(past_ids)},
        navigate=nav, ok=run.status != RunStatus.failed,
    )


@tool("run_exam_audit", "Start an Exam Paper Audit on a question paper (waits for the result by default).", RunAuditArgs, Permission.runs_start)
async def run_exam_audit(env: ToolEnv, a: RunAuditArgs) -> ToolResult:
    cid = await _resolve_course(env, a.course)
    draft = _uuid(a.draft_artefact_id) if a.draft_artefact_id else None
    past = [p for p in (_uuid(x) for x in a.past_artefact_ids or []) if p] if a.past_artefact_ids is not None else None
    return await _run_exam_audit(env, cid, draft, past, a.wait)


class RunRef(BaseModel):
    run_id: str


@tool("get_run", "Status, summary and findings of a run.", RunRef)
async def get_run(env: ToolEnv, a: RunRef) -> ToolResult:
    rid = _uuid(a.run_id)
    if not rid:
        raise ToolError("run_id must be a uuid")
    svc = RunService(env.db, env.user)
    run = await svc.get(rid)
    findings = await svc.findings(rid, type_=None, status=None, severity=None)
    return ToolResult(summary=f"Run {run.status.value} with {len(findings)} findings", data={"run": _run_brief(run), "findings": [_finding_brief(f) for f in findings[:25]]}, navigate=f"/courses/{run.course_id}/exam-audit/{run.id}")


class ListFindingsArgs(CourseRef):
    run_id: str | None = Field(None, description="defaults to the latest finished run of the course")
    status: FindingStatus | None = None
    type: FindingType | None = None


async def _latest_run(env: ToolEnv, cid: uuid.UUID):  # noqa: ANN202
    runs, _ = await RunService(env.db, env.user).list_for_course(cid, module=None, status=None, page=1, page_size=10)
    finished = [r for r in runs if r.status in (RunStatus.completed, RunStatus.partial)]
    if not finished:
        raise ToolError("The course has no finished run yet")
    return finished[0]


@tool("list_findings", "Findings of a run (or of the course's latest run), optionally filtered by status/type.", ListFindingsArgs)
async def list_findings(env: ToolEnv, a: ListFindingsArgs) -> ToolResult:
    svc = RunService(env.db, env.user)
    rid = _uuid(a.run_id) if a.run_id else None
    if rid is None:
        cid = await _resolve_course(env, a.course)
        run = await _latest_run(env, cid)
        rid = run.id
    else:
        run = await svc.get(rid)
    findings = await svc.findings(rid, type_=a.type, status=a.status, severity=None)
    return ToolResult(summary=f"{len(findings)} finding(s) in run {str(rid)[:8]}", data={"run": _run_brief(run), "findings": [_finding_brief(f) for f in findings[:40]]}, navigate=f"/courses/{run.course_id}/exam-audit/{rid}")


class DecideArgs(CourseRef):
    status: FindingStatus
    finding_ids: list[str] | None = Field(None, description="omit to target every open finding of the run")
    run_id: str | None = None
    type: FindingType | None = Field(None, description="restrict 'all' to one finding type")


@tool("decide_findings", "Accept, dismiss or reopen findings — specific ids or all open findings of a run.", DecideArgs, Permission.findings_decide)
async def decide_findings(env: ToolEnv, a: DecideArgs) -> ToolResult:
    svc = RunService(env.db, env.user)
    ids = [x for x in (_uuid(i) for i in a.finding_ids or []) if x]
    run = None
    if not ids:
        rid = _uuid(a.run_id) if a.run_id else None
        run = await svc.get(rid) if rid else await _latest_run(env, await _resolve_course(env, a.course))
        ids = [f.id for f in await svc.findings(run.id, type_=a.type, status=FindingStatus.open if a.status != FindingStatus.open else None, severity=None)]
    done = [await svc.decide(fid, a.status) for fid in ids]
    nav = f"/courses/{run.course_id}/exam-audit/{run.id}" if run else None
    return ToolResult(summary=f"{len(done)} finding(s) marked {a.status.value}", data={"findings": [_finding_brief(f) for f in done[:40]]}, navigate=nav)


class ExportArgs(BaseModel):
    run_id: str
    include: Literal["accepted", "all"] = "accepted"


@tool("export_run", "Markdown report of a finished run (accepted findings by default).", ExportArgs)
async def export_run(env: ToolEnv, a: ExportArgs) -> ToolResult:
    rid = _uuid(a.run_id)
    if not rid:
        raise ToolError("run_id must be a uuid")
    md, filename = await RunService(env.db, env.user).export_markdown(rid, a.include)
    return ToolResult(summary=f"Report {filename} ({len(md)} chars)", data={"filename": filename, "markdown": md[:6000]})


# --- demo & composite ----------------------------------------------------------
@tool("seed_demo", "Create the sample CSE 3103 demo course (idempotent).", NoArgs, Permission.demo_seed)
async def seed_demo_tool(env: ToolEnv, _: NoArgs) -> ToolResult:
    course, created = await seed_demo(env.db, env.user)
    return ToolResult(summary=("Created" if created else "Already present") + f" demo course {course.code}", data={"course": {"id": str(course.id), "code": course.code, "title": course.title, "created": created}}, navigate=f"/courses/{course.id}")


class AnalyzeArgs(UploadArgs):
    compare_with_past_papers: bool = True


@tool(
    "analyze_attachment",
    "Upload the attached file to a course, wait for extraction and — for question papers when the course has COs — run an Exam Paper Audit and return its findings.",
    AnalyzeArgs, Permission.artefacts_write,
)
async def analyze_attachment(env: ToolEnv, a: AnalyzeArgs) -> ToolResult:
    cid, art = await _upload_attachment(env, UploadArgs(**a.model_dump(exclude={"compare_with_past_papers"})))
    data: dict[str, Any] = {"artefact": _artefact_brief(art)}
    if art.status == ExtractionStatus.failed:
        return ToolResult(summary=f"Uploaded '{art.label}' but extraction failed: {art.error}", data=data, navigate=f"/courses/{cid}", ok=False)
    if art.kind != ArtefactKind.question_paper:
        return ToolResult(summary=f"Uploaded '{art.label}' as {art.kind.value}; extraction done", data=data, navigate=f"/courses/{cid}")
    cos = await OutcomeService(env.db, env.user).list_outcomes(cid)
    if not cos:
        return ToolResult(summary=f"Uploaded '{art.label}' ({art.counts.questions if art.counts else '?'} questions). The course has no course outcomes yet, so the exam audit cannot run — add COs first.", data=data, navigate=f"/courses/{cid}")
    past = None if a.compare_with_past_papers else []
    res = await _run_exam_audit(env, cid, art.id, past, wait=True)
    res.data = {**data, **res.data}
    res.summary = f"Uploaded '{art.label}' ({art.counts.questions if art.counts else '?'} questions). " + res.summary
    return res
