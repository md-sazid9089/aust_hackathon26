from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.ai.client import CallContext, structured_call
from app.ai.guard import wrap_untrusted
from app.artefacts.parsers import detect_lang
from app.artefacts.repository import ArtefactRepo
from app.db.enums import ArtefactKind, ExtractionStatus, TextLang, UsagePurpose
from app.db.models import Artefact, Question, Topic
from app.db.session import session_scope
from app.extraction import prompts as P
from app.extraction.schemas import ExtractedQuestions, ExtractedTopics
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
            else:
                error = None  # text-only kinds: nothing more to derive in this build
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
    for q in out.questions:
        number = "".join(q.number.split())
        body = q.text.strip()
        if not number or not body or number in seen:
            continue
        seen.add(number)
        db.add(Question(artefact_id=artefact.id, number=number, text=body[:5000], marks=max(0.0, float(q.marks)), sort_order=order))
        order += 1
    if order == 0:
        return "No questions could be identified in the document"
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
