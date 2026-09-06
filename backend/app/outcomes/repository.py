from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CoPoMap, CourseOutcome, ProgramOutcome, QuestionCoMap, QuestionTopicMap, Topic


class OutcomeRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def program_outcomes(self) -> list[ProgramOutcome]:
        stmt = select(ProgramOutcome).order_by(ProgramOutcome.sort_order, ProgramOutcome.code)
        return list((await self.db.execute(stmt)).scalars().all())

    async def course_outcomes(self, course_id: uuid.UUID) -> list[CourseOutcome]:
        stmt = (
            select(CourseOutcome)
            .where(CourseOutcome.course_id == course_id)
            .order_by(CourseOutcome.sort_order, CourseOutcome.code)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def co_in_use(self, co_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        if not co_ids:
            return []
        stmt = select(QuestionCoMap.co_id).where(QuestionCoMap.co_id.in_(co_ids)).distinct()
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete_cos(self, ids: list[uuid.UUID]) -> None:
        if ids:
            await self.db.execute(delete(CourseOutcome).where(CourseOutcome.id.in_(ids)))

    async def co_po_map(self, course_id: uuid.UUID) -> list[CoPoMap]:
        stmt = (
            select(CoPoMap)
            .join(CourseOutcome, CourseOutcome.id == CoPoMap.co_id)
            .where(CourseOutcome.course_id == course_id)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def replace_co_po_map(self, course_id: uuid.UUID, cells: list[CoPoMap]) -> None:
        co_ids = select(CourseOutcome.id).where(CourseOutcome.course_id == course_id)
        await self.db.execute(delete(CoPoMap).where(CoPoMap.co_id.in_(co_ids)))
        self.db.add_all(cells)

    async def topics(self, course_id: uuid.UUID) -> list[Topic]:
        stmt = select(Topic).where(Topic.course_id == course_id).order_by(Topic.sort_order, Topic.code)
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete_topics(self, ids: list[uuid.UUID]) -> None:
        if ids:
            await self.db.execute(delete(QuestionTopicMap).where(QuestionTopicMap.topic_id.in_(ids)))
            await self.db.execute(delete(Topic).where(Topic.id.in_(ids)))

    async def count_cos(self, course_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(CourseOutcome.course_id == course_id)
        return (await self.db.execute(stmt)).scalar_one()
