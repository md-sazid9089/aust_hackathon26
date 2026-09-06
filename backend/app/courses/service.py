from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.courses.repository import CourseRepo
from app.courses.schemas import CourseCounts, CourseCreate, CourseOut, CourseUpdate
from app.db.models import Course, Profile, utcnow
from app.errors import Conflict, NotFound
from app.logging import get_logger

log = get_logger(__name__)


async def get_owned_course(db: AsyncSession, course_id: uuid.UUID, user: Profile) -> Course:
    """Ownership check shared by every course-scoped module. Non-owners get 404 (no existence leak)."""
    course = await CourseRepo(db).get(course_id)
    if course is None or course.owner_id != user.id:
        raise NotFound("COURSE_NOT_FOUND", "Course not found")
    return course


class CourseService:
    def __init__(self, db: AsyncSession, user: Profile) -> None:
        self.db = db
        self.user = user
        self.repo = CourseRepo(db)

    async def list(self, *, q: str | None, page: int, page_size: int, sort: str) -> tuple[list[CourseOut], int]:
        desc = not sort.endswith(":asc")
        rows, total = await self.repo.list(
            self.user.id, q=q, offset=(page - 1) * page_size, limit=page_size, sort_desc=desc
        )
        return [CourseOut.model_validate(c) for c in rows], total

    async def create(self, data: CourseCreate) -> CourseOut:
        if await self.repo.get_by_code(self.user.id, data.code):
            raise Conflict("COURSE_CODE_EXISTS", "A course with this code already exists")
        course = Course(owner_id=self.user.id, **data.model_dump())
        self.repo.add(course)
        await self.db.flush()
        log.info("course.created", course_id=str(course.id))
        return CourseOut.model_validate(course)

    async def get(self, course_id: uuid.UUID) -> CourseOut:
        course = await get_owned_course(self.db, course_id, self.user)
        out = CourseOut.model_validate(course)
        out.counts = CourseCounts(**await self.repo.counts(course.id))
        return out

    async def update(self, course_id: uuid.UUID, data: CourseUpdate) -> CourseOut:
        course = await get_owned_course(self.db, course_id, self.user)
        changes = data.model_dump(exclude_unset=True)
        if "code" in changes and changes["code"] != course.code:
            if await self.repo.get_by_code(self.user.id, changes["code"]):
                raise Conflict("COURSE_CODE_EXISTS", "A course with this code already exists")
        for k, v in changes.items():
            setattr(course, k, v)
        await self.db.flush()
        return CourseOut.model_validate(course)

    async def delete(self, course_id: uuid.UUID) -> None:
        course = await get_owned_course(self.db, course_id, self.user)
        course.deleted_at = utcnow()
        await self.db.flush()
