from __future__ import annotations

import uuid

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.artefacts import parsers
from app.artefacts.repository import ArtefactRepo
from app.artefacts.schemas import (
    AnswerIn,
    AnswerOut,
    ArtefactCounts,
    ArtefactOut,
    MarksQuestionOut,
    MarksRowOut,
    MarksSheetOut,
    QuestionCoMapIn,
    QuestionIn,
    QuestionOut,
    RubricCriterionIn,
    RubricCriterionOut,
)
from app.artefacts.storage import get_storage, object_path
from app.config import get_settings
from app.courses.service import get_owned_course
from app.db.enums import SUPPORTED_ARTEFACT_KINDS, ArtefactKind, ExtractionStatus, MapSource
from app.db.models import Answer, Artefact, Profile, Question, QuestionCoMap, RubricCriterion
from app.errors import ApiError, Conflict, NotFound
from app.extraction.service import schedule_extraction
from app.logging import get_logger
from app.outcomes.repository import OutcomeRepo

log = get_logger(__name__)

SAFE_LABEL_MAX = 200


class ArtefactService:
    def __init__(self, db: AsyncSession, user: Profile) -> None:
        self.db = db
        self.user = user
        self.repo = ArtefactRepo(db)

    async def _owned(self, artefact_id: uuid.UUID) -> Artefact:
        artefact = await self.repo.get(artefact_id)
        if artefact is None:
            raise NotFound("ARTEFACT_NOT_FOUND", "Artefact not found")
        await get_owned_course(self.db, artefact.course_id, self.user)  # 404 if not owner
        return artefact

    async def _out(self, artefact: Artefact, with_counts: bool = True) -> ArtefactOut:
        out = ArtefactOut.model_validate(artefact)
        if with_counts:
            out.counts = ArtefactCounts(**await self.repo.counts(artefact.id))
        return out

    async def create(
        self,
        course_id: uuid.UUID,
        *,
        kind: ArtefactKind,
        label: str,
        year: int | None,
        term: str | None,
        declared_total_marks: float | None,
        file: UploadFile | None,
        text: str | None,
    ) -> ArtefactOut:
        await get_owned_course(self.db, course_id, self.user)
        if kind not in SUPPORTED_ARTEFACT_KINDS:
            raise ApiError(
                "ARTEFACT_KIND_NOT_SUPPORTED", 422,
                f"Artefact kind '{kind.value}' is not supported in this build",
                {"supported": sorted(k.value for k in SUPPORTED_ARTEFACT_KINDS)},
            )
        if (file is None or not file.filename) == (not (text and text.strip())):
            raise ApiError("VALIDATION_ERROR", 422, "Provide exactly one of `file` or `text`")
        settings = get_settings()
        artefact = Artefact(
            course_id=course_id, kind=kind, label=label.strip()[:SAFE_LABEL_MAX], year=year, term=term,
            declared_total_marks=declared_total_marks, status=ExtractionStatus.pending,
        )
        if file is not None and file.filename:
            data = await file.read(settings.max_upload_bytes + 1)
            if len(data) > settings.max_upload_bytes:
                raise ApiError("FILE_TOO_LARGE", 413, f"File exceeds {settings.max_upload_mb} MB")
            if not data:
                raise ApiError("VALIDATION_ERROR", 422, "Empty file")
            try:
                ext = parsers.sniff_extension(file.filename, data[:1024])
                extracted = parsers.extract_text(ext, data)
            except parsers.UnsupportedFile as exc:
                raise ApiError("UNSUPPORTED_FILE_TYPE", 415, str(exc)) from exc
            except parsers.NoTextExtracted as exc:
                raise ApiError("ARTEFACT_NO_TEXT", 422, str(exc)) from exc
            artefact.mime = parsers.CANONICAL_MIME[ext]
            artefact.size_bytes = len(data)
            artefact.storage_path = object_path(course_id, artefact.id, ext)
            artefact.extracted_text = extracted
            await get_storage().put(artefact.storage_path, data)
        else:
            cleaned = parsers.normalise_text(text or "")
            if len(cleaned) < 20:
                raise ApiError("ARTEFACT_NO_TEXT", 422, "Pasted text is too short")
            if len(cleaned) > 200_000:
                raise ApiError("FILE_TOO_LARGE", 413, "Pasted text is too long")
            artefact.mime = "text/plain"
            artefact.size_bytes = len(cleaned.encode())
            artefact.extracted_text = cleaned
        self.db.add(artefact)
        await self.db.flush()
        out = await self._out(artefact, with_counts=False)
        await self.db.commit()  # visible to the background task's own session
        schedule_extraction(artefact.id, self.user.id)
        out.status = ExtractionStatus.extracting  # reported state; ORM row is left untouched
        log.info("artefact.uploaded", artefact_id=str(artefact.id), kind=kind.value)
        return out

    async def list(self, course_id: uuid.UUID, *, kind: ArtefactKind | None, status: ExtractionStatus | None) -> list[ArtefactOut]:
        await get_owned_course(self.db, course_id, self.user)
        return [await self._out(a) for a in await self.repo.list(course_id, kind=kind, status=status)]

    async def get(self, artefact_id: uuid.UUID) -> ArtefactOut:
        return await self._out(await self._owned(artefact_id))

    async def get_text(self, artefact_id: uuid.UUID) -> Artefact:
        return await self._owned(artefact_id)

    async def delete(self, artefact_id: uuid.UUID) -> None:
        artefact = await self._owned(artefact_id)
        if await self.repo.referenced_by_runs(artefact.id, completed_only=True):
            raise Conflict("ARTEFACT_IN_USE", "Artefact is referenced by a completed run")
        await self.repo.delete_run_inputs(artefact.id)
        await self.repo.clear_children(artefact)
        if artefact.storage_path:
            await get_storage().delete(artefact.storage_path)
        await self.db.delete(artefact)
        await self.db.flush()

    async def reextract(self, artefact_id: uuid.UUID) -> ArtefactOut:
        artefact = await self._owned(artefact_id)
        if artefact.status == ExtractionStatus.extracting:
            raise Conflict("ARTEFACT_NOT_READY", "Extraction already in progress")
        if await self.repo.referenced_by_runs(artefact.id, completed_only=True):
            raise Conflict("ARTEFACT_IN_USE", "Artefact is referenced by a completed run; upload a new version instead")
        artefact.status = ExtractionStatus.pending
        artefact.error = None
        out = await self._out(artefact, with_counts=False)
        await self.db.commit()
        schedule_extraction(artefact.id, self.user.id)
        out.status = ExtractionStatus.extracting
        return out

    # --- questions ----------------------------------------------------------
    async def questions(self, artefact_id: uuid.UUID) -> list[QuestionOut]:
        artefact = await self._owned(artefact_id)
        return [self._question_out(q) for q in await self.repo.questions(artefact.id)]

    @staticmethod
    def _question_out(q: Question) -> QuestionOut:
        out = QuestionOut.model_validate(q)
        out.co_ids = [l.co_id for l in q.co_links]
        out.topic_ids = [l.topic_id for l in q.topic_links]
        return out

    async def replace_questions(self, artefact_id: uuid.UUID, items: list[QuestionIn]) -> list[QuestionOut]:
        """Faculty confirm/edit step. Edited text clears the embedding so duplicates are recomputed."""
        artefact = await self._owned(artefact_id)
        if artefact.kind != ArtefactKind.question_paper:
            raise ApiError("VALIDATION_ERROR", 422, "Questions can only be edited on question papers")
        if artefact.status == ExtractionStatus.extracting:
            raise Conflict("ARTEFACT_NOT_READY", "Extraction in progress")
        numbers = [i.number for i in items]
        if len(set(numbers)) != len(numbers):
            raise ApiError("VALIDATION_ERROR", 422, "Duplicate question numbers")
        existing = {q.id: q for q in await self.repo.questions(artefact.id)}
        keep = {i.id for i in items if i.id}
        if keep - set(existing):
            raise ApiError("VALIDATION_ERROR", 422, "Unknown question ids")
        await self.repo.delete_questions([qid for qid in existing if qid not in keep])
        for order, item in enumerate(items):
            if item.id:
                row = existing[item.id]
                if row.text != item.text:
                    row.embedding, row.embedding_model = None, None
                row.number, row.text, row.marks, row.sort_order = item.number, item.text, item.marks, order
            else:
                self.db.add(Question(artefact_id=artefact.id, number=item.number, text=item.text, marks=item.marks, sort_order=order))
        if artefact.status == ExtractionStatus.failed and items:
            artefact.status, artefact.error = ExtractionStatus.done, None
        await self.db.flush()
        return await self.questions(artefact_id)

    async def set_co_map(self, artefact_id: uuid.UUID, items: list[QuestionCoMapIn]) -> list[QuestionOut]:
        artefact = await self._owned(artefact_id)
        questions = {q.id: q for q in await self.repo.questions(artefact.id)}
        co_ids = {c.id for c in await OutcomeRepo(self.db).course_outcomes(artefact.course_id)}
        rows: list[QuestionCoMap] = []
        for item in items:
            if item.question_id not in questions:
                raise ApiError("VALIDATION_ERROR", 422, "Unknown question id", {"question_id": str(item.question_id)})
            bad = [str(c) for c in item.co_ids if c not in co_ids]
            if bad:
                raise ApiError("VALIDATION_ERROR", 422, "Unknown outcome ids", {"co_ids": bad})
            for co in dict.fromkeys(item.co_ids):
                rows.append(QuestionCoMap(question_id=item.question_id, co_id=co, source=MapSource.faculty, confidence=1.0))
        await self.repo.replace_co_map([i.question_id for i in items], rows)
        await self.db.flush()
        return await self.questions(artefact_id)

    # --- marks sheet ----------------------------------------------------------
    async def marks(self, artefact_id: uuid.UUID) -> MarksSheetOut:
        artefact = await self._owned_kind(artefact_id, ArtefactKind.marks_sheet)
        cols = await self.repo.marks_columns(artefact.id)
        rows = await self.repo.marks_rows(artefact.id)
        return MarksSheetOut(
            students=len(rows),
            questions=[MarksQuestionOut(number=c.number, max=c.max_marks, co_code=c.co_code) for c in cols],
            rows=[MarksRowOut(student_anon_id=r.student_anon_id, scores={k: float(v) for k, v in r.scores.items()}) for r in rows],
        )

    # --- rubric -----------------------------------------------------------------
    async def rubric(self, artefact_id: uuid.UUID) -> list[RubricCriterionOut]:
        artefact = await self._owned_kind(artefact_id, ArtefactKind.rubric)
        return [RubricCriterionOut.model_validate(c) for c in await self.repo.rubric(artefact.id)]

    async def replace_rubric(self, artefact_id: uuid.UUID, items: list[RubricCriterionIn]) -> list[RubricCriterionOut]:
        artefact = await self._owned_kind(artefact_id, ArtefactKind.rubric, for_write=True)
        codes = [i.code for i in items]
        if len(set(codes)) != len(codes):
            raise ApiError("VALIDATION_ERROR", 422, "Duplicate criterion codes")
        existing = {c.id: c for c in await self.repo.rubric(artefact.id)}
        keep = {i.id for i in items if i.id}
        if keep - set(existing):
            raise ApiError("VALIDATION_ERROR", 422, "Unknown criterion ids")
        for cid, row in existing.items():
            if cid not in keep:
                await self.db.delete(row)
        for order, item in enumerate(items):
            levels = [lv.model_dump() for lv in item.levels]
            if item.id:
                row = existing[item.id]
                row.code, row.text, row.max_score, row.levels, row.sort_order = item.code, item.text, item.max_score, levels, order
            else:
                self.db.add(RubricCriterion(artefact_id=artefact.id, code=item.code, text=item.text, max_score=item.max_score, levels=levels, sort_order=order))
        if artefact.status == ExtractionStatus.failed and items:
            artefact.status, artefact.error = ExtractionStatus.done, None
        await self.db.flush()
        return await self.rubric(artefact_id)

    # --- answer set ---------------------------------------------------------------
    async def answers(self, artefact_id: uuid.UUID) -> list[AnswerOut]:
        artefact = await self._owned_kind(artefact_id, ArtefactKind.answer_set)
        return [AnswerOut.model_validate(a) for a in await self.repo.answers(artefact.id)]

    async def replace_answers(self, artefact_id: uuid.UUID, items: list[AnswerIn]) -> list[AnswerOut]:
        artefact = await self._owned_kind(artefact_id, ArtefactKind.answer_set, for_write=True)
        existing = {a.id: a for a in await self.repo.answers(artefact.id)}
        keep = {i.id for i in items if i.id}
        if keep - set(existing):
            raise ApiError("VALIDATION_ERROR", 422, "Unknown answer ids")
        for aid, row in existing.items():
            if aid not in keep:
                await self.db.delete(row)
        for order, item in enumerate(items):
            scores = [g.model_dump() for g in item.grader_scores]
            if item.id:
                row = existing[item.id]
                row.student_anon_id, row.question_ref, row.text, row.grader_scores, row.sort_order = (
                    item.student_anon_id, item.question_ref, item.text, scores, order,
                )
            else:
                self.db.add(Answer(artefact_id=artefact.id, student_anon_id=item.student_anon_id, question_ref=item.question_ref,
                                   text=item.text, grader_scores=scores, sort_order=order))
        if artefact.status == ExtractionStatus.failed and items:
            artefact.status, artefact.error = ExtractionStatus.done, None
        await self.db.flush()
        return await self.answers(artefact_id)

    async def _owned_kind(self, artefact_id: uuid.UUID, kind: ArtefactKind, *, for_write: bool = False) -> Artefact:
        artefact = await self._owned(artefact_id)
        if artefact.kind != kind:
            raise ApiError("VALIDATION_ERROR", 422, f"Artefact is a {artefact.kind.value}, not a {kind.value}")
        if for_write and artefact.status == ExtractionStatus.extracting:
            raise Conflict("ARTEFACT_NOT_READY", "Extraction in progress")
        return artefact
