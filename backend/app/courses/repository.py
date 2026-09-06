from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artefact, Course, CourseOutcome, Run


class CourseRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _active(self, owner_id: uuid.UUID):
        return select(Course).where(Course.owner_id == owner_id, Course.deleted_at.is_(None))

    async def list(
        self, owner_id: uuid.UUID, *, q: str | None, offset: int, limit: int, sort_desc: bool
    ) -> tuple[list[Course], int]:
        stmt = self._active(owner_id)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(or_(Course.code.ilike(pattern), Course.title.ilike(pattern)))
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        order = Course.created_at.desc() if sort_desc else Course.created_at.asc()
        rows = (await self.db.execute(stmt.order_by(order).offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def get(self, course_id: uuid.UUID) -> Course | None:
        stmt = select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, owner_id: uuid.UUID, code: str) -> Course | None:
        stmt = self._active(owner_id).where(Course.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def counts(self, course_id: uuid.UUID) -> dict[str, int]:
        async def _count(model, col):  # noqa: ANN001
            return (await self.db.execute(select(func.count()).where(col == course_id))).scalar_one()

        return {
            "artefacts": await _count(Artefact, Artefact.course_id),
            "runs": await _count(Run, Run.course_id),
            "outcomes": await _count(CourseOutcome, CourseOutcome.course_id),
        }

    def add(self, course: Course) -> None:
        self.db.add(course)
