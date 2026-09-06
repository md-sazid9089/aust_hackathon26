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
    ) -> tuple[list[tuple[Course, dict[str, int]]], int]:
        stmt = self._active(owner_id)
        if q:
            escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            stmt = stmt.where(or_(Course.code.ilike(pattern, escape="\\"), Course.title.ilike(pattern, escape="\\")))
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        order = Course.created_at.desc() if sort_desc else Course.created_at.asc()
        # Counts as correlated subqueries so the whole page loads in a single round-trip (no per-course N+1).
        art_c = select(func.count()).where(Artefact.course_id == Course.id).correlate(Course).scalar_subquery()
        run_c = select(func.count()).where(Run.course_id == Course.id).correlate(Course).scalar_subquery()
        out_c = select(func.count()).where(CourseOutcome.course_id == Course.id).correlate(Course).scalar_subquery()
        page = stmt.add_columns(art_c, run_c, out_c).order_by(order).offset(offset).limit(limit)
        rows = (await self.db.execute(page)).all()
        return [(r[0], {"artefacts": r[1], "runs": r[2], "outcomes": r[3]}) for r in rows], total

    async def get(self, course_id: uuid.UUID) -> Course | None:
        stmt = select(Course).where(Course.id == course_id, Course.deleted_at.is_(None))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_code(self, owner_id: uuid.UUID, code: str) -> Course | None:
        stmt = self._active(owner_id).where(Course.code == code)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def counts(self, course_id: uuid.UUID) -> dict[str, int]:
        # Single round-trip: three scalar subqueries in one SELECT.
        art_c = select(func.count()).where(Artefact.course_id == course_id).scalar_subquery()
        run_c = select(func.count()).where(Run.course_id == course_id).scalar_subquery()
        out_c = select(func.count()).where(CourseOutcome.course_id == course_id).scalar_subquery()
        a, r, o = (await self.db.execute(select(art_c, run_c, out_c))).one()
        return {"artefacts": a, "runs": r, "outcomes": o}

    def add(self, course: Course) -> None:
        self.db.add(course)
