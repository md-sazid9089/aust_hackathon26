from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.courses.service import get_owned_course
from app.db.models import CoPoMap, CourseOutcome, Profile, Topic
from app.errors import ApiError, Conflict
from app.outcomes.repository import OutcomeRepo
from app.outcomes.schemas import (
    CoPoCell,
    CourseOutcomeIn,
    CourseOutcomeOut,
    ProgramOutcomeOut,
    TopicIn,
    TopicOut,
)


def _check_unique_codes(items: list, what: str) -> None:
    codes = [i.code for i in items]
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    if dupes:
        raise ApiError("VALIDATION_ERROR", 422, f"Duplicate {what} codes", {"codes": dupes})


class OutcomeService:
    def __init__(self, db: AsyncSession, user: Profile) -> None:
        self.db = db
        self.user = user
        self.repo = OutcomeRepo(db)

    async def program_outcomes(self) -> list[ProgramOutcomeOut]:
        return [ProgramOutcomeOut.model_validate(p) for p in await self.repo.program_outcomes()]

    async def list_outcomes(self, course_id: uuid.UUID) -> list[CourseOutcomeOut]:
        await get_owned_course(self.db, course_id, self.user)
        return [CourseOutcomeOut.model_validate(c) for c in await self.repo.course_outcomes(course_id)]

    async def replace_outcomes(self, course_id: uuid.UUID, items: list[CourseOutcomeIn]) -> list[CourseOutcomeOut]:
        """Replace-all in one transaction: delete missing, update by id, insert new."""
        await get_owned_course(self.db, course_id, self.user)
        _check_unique_codes(items, "outcome")
        existing = {c.id: c for c in await self.repo.course_outcomes(course_id)}
        keep = {i.id for i in items if i.id}
        unknown = keep - set(existing)
        if unknown:
            raise ApiError("VALIDATION_ERROR", 422, "Unknown outcome ids", {"ids": [str(u) for u in unknown]})
        to_delete = [cid for cid in existing if cid not in keep]
        in_use = await self.repo.co_in_use(to_delete)
        if in_use:
            raise Conflict(
                "OUTCOME_IN_USE",
                "Some outcomes are referenced by question mappings and cannot be deleted",
                {"ids": [str(i) for i in in_use], "codes": [existing[i].code for i in in_use]},
            )
        await self.repo.delete_cos(to_delete)
        for order, item in enumerate(items):
            if item.id:
                row = existing[item.id]
                row.code, row.text, row.bloom_level, row.weight, row.sort_order = (
                    item.code, item.text, item.bloom_level, item.weight, order,
                )
            else:
                self.db.add(
                    CourseOutcome(
                        course_id=course_id, code=item.code, text=item.text,
                        bloom_level=item.bloom_level, weight=item.weight, sort_order=order,
                    )
                )
        await self.db.flush()
        return [CourseOutcomeOut.model_validate(c) for c in await self.repo.course_outcomes(course_id)]

    async def co_po_map(self, course_id: uuid.UUID) -> list[CoPoCell]:
        await get_owned_course(self.db, course_id, self.user)
        return [CoPoCell.model_validate(c) for c in await self.repo.co_po_map(course_id)]

    async def replace_co_po_map(self, course_id: uuid.UUID, cells: list[CoPoCell]) -> list[CoPoCell]:
        await get_owned_course(self.db, course_id, self.user)
        co_ids = {c.id for c in await self.repo.course_outcomes(course_id)}
        po_ids = {p.id for p in await self.repo.program_outcomes()}
        bad = [c for c in cells if c.co_id not in co_ids or c.po_id not in po_ids]
        if bad:
            raise ApiError("VALIDATION_ERROR", 422, "Cells reference unknown CO/PO ids")
        seen = {(c.co_id, c.po_id) for c in cells}
        if len(seen) != len(cells):
            raise ApiError("VALIDATION_ERROR", 422, "Duplicate CO/PO cells")
        await self.repo.replace_co_po_map(
            course_id, [CoPoMap(co_id=c.co_id, po_id=c.po_id, strength=c.strength) for c in cells]
        )
        await self.db.flush()
        return await self.co_po_map(course_id)

    async def topics(self, course_id: uuid.UUID) -> list[TopicOut]:
        await get_owned_course(self.db, course_id, self.user)
        return [TopicOut.model_validate(t) for t in await self.repo.topics(course_id)]

    async def replace_topics(self, course_id: uuid.UUID, items: list[TopicIn]) -> list[TopicOut]:
        await get_owned_course(self.db, course_id, self.user)
        _check_unique_codes(items, "topic")
        existing = {t.id: t for t in await self.repo.topics(course_id)}
        keep = {i.id for i in items if i.id}
        unknown = keep - set(existing)
        if unknown:
            raise ApiError("VALIDATION_ERROR", 422, "Unknown topic ids", {"ids": [str(u) for u in unknown]})
        await self.repo.delete_topics([tid for tid in existing if tid not in keep])
        for order, item in enumerate(items):
            if item.id:
                row = existing[item.id]
                if row.title != item.title:
                    row.embedding, row.embedding_model = None, None
                row.code, row.title, row.sort_order = item.code, item.title, order
            else:
                self.db.add(Topic(course_id=course_id, code=item.code, title=item.title, sort_order=order))
        await self.db.flush()
        return await self.topics(course_id)
