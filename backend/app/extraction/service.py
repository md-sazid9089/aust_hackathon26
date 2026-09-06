from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.ai.client import CallContext, structured_call
from app.ai.guard import wrap_untrusted
from app.artefacts import parsers
from app.artefacts.parsers import detect_lang
from app.artefacts.repository import ArtefactRepo
from app.db.enums import ArtefactKind, ExtractionStatus, TextLang, UsagePurpose
from app.db.models import Answer, Artefact, MarksColumn, MarksRow, Question, RubricCriterion, Topic
from app.db.session import session_scope
from app.extraction import prompts as P
from app.extraction.schemas import ExtractedAnswers, ExtractedQuestions, ExtractedRubric, ExtractedTopics
from app.logging import get_logger

log = get_logger(__name__)

# Registry of in-flight extraction tasks (observability + tests can await them).
_tasks: dict[uuid.UUID, asyncio.Task] = {}


def schedule_extraction(artefact_id: uuid.UUID, owner_id: uuid.UUID) -> asyncio.Task:
    task = asyncio.create_task(run_extraction(artefact_id, owner_id), name=f"extract:{artefact_id}")
    _tasks[artefact_id] = task
    task.add_done_callback(lambda t: _tasks.pop(artefact_id, None))
    return task


async def wait_for_extractions() -> None:
    if _tasks:
        await asyncio.gather(*list(_tasks.values()), return_exceptions=True)


def extraction_task(artefact_id: uuid.UUID) -> asyncio.Task | None:
    """In-flight extraction task for an artefact, if any (assistant awaits it)."""
    return _tasks.get(artefact_id)


async def run_extraction(artefact_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    """Background task: extracted_text -> LLM structured extraction -> child rows. Own DB session."""
    ctx = CallContext(user_id=owner_id)
    try:
        async with session_scope() as db:
            artefact = await db.get(Artefact, artefact_id)
            if artefact is None:
                return
            artefact.status = ExtractionStatus.extracting
            artefact.error = None
        async with session_scope() as db:
            artefact = await db.get(Artefact, artefact_id)
            assert artefact is not None
            text = artefact.extracted_text or ""
            artefact.lang = TextLang(detect_lang(text))
            repo = ArtefactRepo(db)
            await repo.clear_children(artefact)
            if artefact.kind == ArtefactKind.question_paper:
                error = await _extract_questions(db, artefact, text, ctx)
            elif artefact.kind == ArtefactKind.syllabus:
                error = await _extract_topics(db, artefact, text, ctx)
            elif artefact.kind == ArtefactKind.marks_sheet:
                error = _extract_marks(db, artefact, text)
            elif artefact.kind == ArtefactKind.rubric:
                error = await _extract_rubric(db, artefact, text, ctx)
            elif artefact.kind == ArtefactKind.answer_set:
                error = await _extract_answers(db, artefact, text, ctx)
            else:
                error = None
            if error:
                artefact.status = ExtractionStatus.failed
                artefact.error = error
                log.warning("extraction.failed", artefact_id=str(artefact_id), error=error)
            else:
                artefact.status = ExtractionStatus.done
                log.info("extraction.completed", artefact_id=str(artefact_id), kind=artefact.kind.value)
    except Exception:  # noqa: BLE001 - background task must never die silently
        log.exception("extraction.crashed", artefact_id=str(artefact_id))
        try:
            async with session_scope() as db:
                artefact = await db.get(Artefact, artefact_id)
                if artefact is not None:
                    artefact.status = ExtractionStatus.failed
                    artefact.error = "Extraction failed unexpectedly"
        except Exception:  # noqa: BLE001
            log.exception("extraction.mark_failed_failed", artefact_id=str(artefact_id))


async def _extract_questions(db, artefact: Artefact, text: str, ctx: CallContext) -> str | None:
    res = await structured_call(
        purpose="extract_questions",
        usage_purpose=UsagePurpose.extraction,
        system=P.EXTRACT_QUESTIONS_SYSTEM,
        user=P.EXTRACT_QUESTIONS_USER.format(document=wrap_untrusted(text, "paper")),
        schema=ExtractedQuestions,
        ctx=ctx,
        db=db,
        context={"text": text},
    )
    if res.value is None:
        return f"AI extraction unavailable ({res.error}). Paste the questions manually or retry."
    out: ExtractedQuestions = res.value  # type: ignore[assignment]
    seen: set[str] = set()
    order = 0
    src = " ".join(text.lower().split())
    suspicious: list[str] = []
    for q in out.questions:
        number = "".join(q.number.split())
        body = q.text.strip()
        if not number or not body or number in seen:
            continue
        seen.add(number)
        marks = float(q.marks)
        if not (0 <= marks <= 100):  # a single question above 100 marks is a misread, not a fact
            suspicious.append(f"Q{number}: marks {marks:g} out of range, set to 0")
            marks = 0.0
        # Verbatim check: the model must not paraphrase the question; use the first 60 chars as a probe.
        probe = " ".join(body[:60].lower().split())
        if len(probe) >= 12 and probe not in src:
            suspicious.append(f"Q{number}: text not found verbatim in the document")
        db.add(Question(artefact_id=artefact.id, number=number, text=body[:5000], marks=marks, sort_order=order))
        order += 1
    if order == 0:
        return "No questions could be identified in the document"
    if suspicious:
        log.warning("extraction.questions_suspicious", artefact_id=str(artefact.id), count=len(suspicious))
        artefact.error = "Check these extracted items: " + "; ".join(suspicious[:5])  # status stays done; faculty confirms
    return None


async def _extract_topics(db, artefact: Artefact, text: str, ctx: CallContext) -> str | None:
    res = await structured_call(
        purpose="extract_syllabus",
        usage_purpose=UsagePurpose.extraction,
        system=P.EXTRACT_SYLLABUS_SYSTEM,
        user=P.EXTRACT_SYLLABUS_USER.format(document=wrap_untrusted(text, "syllabus")),
        schema=ExtractedTopics,
        ctx=ctx,
        db=db,
        context={"text": text},
    )
    if res.value is None:
        return f"AI extraction unavailable ({res.error}). Enter topics manually or retry."
    out: ExtractedTopics = res.value  # type: ignore[assignment]
    existing_codes = set(
        (await db.execute(select(Topic.code).where(Topic.course_id == artefact.course_id))).scalars()
    )
    order = len(existing_codes)
    added = 0
    for t in out.topics:
        code = " ".join(t.code.strip().upper().split()) or f"T-{order + 1:02d}"
        while code in existing_codes:
            order += 1
            code = f"T-{order + 1:02d}"
        existing_codes.add(code)
        db.add(Topic(course_id=artefact.course_id, code=code, title=t.title.strip()[:500], source_artefact_id=artefact.id, sort_order=order))
        order += 1
        added += 1
    if added == 0:
        return "No topics could be identified in the document"
    return None


def _extract_marks(db, artefact: Artefact, text: str) -> str | None:
    """Deterministic: marks are numbers, never sent to the LLM (AI-004, SEC-007)."""
    try:
        parsed = parsers.parse_marks_csv(text)
    except parsers.NoTextExtracted as exc:
        return str(exc)
    for i, c in enumerate(parsed["columns"]):
        db.add(MarksColumn(artefact_id=artefact.id, number=c["number"], max_marks=float(c["max_marks"] or 0), co_code=c["co_code"], sort_order=i))
    for i, r in enumerate(parsed["rows"]):
        db.add(MarksRow(artefact_id=artefact.id, student_anon_id=r["student_anon_id"][:40], scores=r["scores"], sort_order=i))
    if parsed["warnings"]:
        log.info("extraction.marks_warnings", artefact_id=str(artefact.id), count=len(parsed["warnings"]))
    return None


async def _extract_rubric(db, artefact: Artefact, text: str, ctx: CallContext) -> str | None:
    res = await structured_call(
        purpose="extract_rubric",
        usage_purpose=UsagePurpose.extraction,
        system=P.EXTRACT_RUBRIC_SYSTEM,
        user=P.EXTRACT_RUBRIC_USER.format(document=wrap_untrusted(text, "rubric")),
        schema=ExtractedRubric,
        ctx=ctx,
        db=db,
        context={"text": text},
    )
    if res.value is None:
        return f"AI extraction unavailable ({res.error}). Enter the criteria manually or retry."
    out: ExtractedRubric = res.value  # type: ignore[assignment]
    seen: set[str] = set()
    order = 0
    for c in out.criteria:
        code = "".join(c.code.upper().split()) or f"R{order + 1}"
        if code in seen or not c.text.strip() or c.max_score <= 0:
            continue
        seen.add(code)
        levels = [{"label": lv.label[:40], "score": float(lv.score), "descriptor": lv.descriptor[:2000]} for lv in c.levels[:12]]
        db.add(RubricCriterion(artefact_id=artefact.id, code=code[:20], text=c.text.strip()[:1000], max_score=float(c.max_score), levels=levels, sort_order=order))
        order += 1
    if order == 0:
        return "No rubric criteria could be identified in the document"
    return None


async def _extract_answers(db, artefact: Artefact, text: str, ctx: CallContext) -> str | None:
    res = await structured_call(
        purpose="extract_answers",
        usage_purpose=UsagePurpose.extraction,
        system=P.EXTRACT_ANSWERS_SYSTEM,
        user=P.EXTRACT_ANSWERS_USER.format(document=wrap_untrusted(text, "answers", max_chars=60_000)),
        schema=ExtractedAnswers,
        ctx=ctx,
        db=db,
        context={"text": text},
    )
    if res.value is None:
        return f"AI extraction unavailable ({res.error}). Enter the answers manually or retry."
    out: ExtractedAnswers = res.value  # type: ignore[assignment]
    order = 0
    for a in out.answers:
        body = a.text.strip()
        if not body:
            continue
        scores = [
            {"grader_label": g.grader_label.strip()[:40], "criterion_code": "".join(g.criterion_code.upper().split())[:20], "score": float(g.score)}
            for g in a.grader_scores[:200]
            if g.grader_label.strip() and g.criterion_code.strip()
        ]
        db.add(Answer(artefact_id=artefact.id, student_anon_id=parsers.anonymise_student(a.student_anon_id)[:40],
                      question_ref=(a.question_ref.strip()[:20] or None), text=body[:20_000], grader_scores=scores, sort_order=order))
        order += 1
    if order == 0:
        return "No answers could be identified in the document"
    return None
