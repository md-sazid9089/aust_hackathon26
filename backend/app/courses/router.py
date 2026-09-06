from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.courses.schemas import CourseCreate, CourseOut, CourseUpdate
from app.courses.service import CourseService
from app.db.enums import Permission
from app.deps import DbDep, UserDep, require_permission
from app.schemas import ERROR_RESPONSES, Page

router = APIRouter(prefix="/courses", tags=["courses"])
WRITE = [Depends(require_permission(Permission.courses_write))]


@router.get("", response_model=Page[CourseOut], summary="List my courses", responses=ERROR_RESPONSES)
async def list_courses(
    db: DbDep,
    user: UserDep,
    q: Annotated[str | None, Query(max_length=100, description="Search code/title")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(pattern=r"^created_at:(asc|desc)$")] = "created_at:desc",
) -> Page[CourseOut]:
    items, total = await CourseService(db, user).list(q=q, page=page, page_size=page_size, sort=sort)
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.post(
    "",
    response_model=CourseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a course workspace",
    description="Course code is upper-cased and must be unique per owner (`409 COURSE_CODE_EXISTS`).",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def create_course(data: CourseCreate, db: DbDep, user: UserDep) -> CourseOut:
    return await CourseService(db, user).create(data)


@router.get(
    "/{course_id}",
    response_model=CourseOut,
    summary="Get a course with counts",
    responses=ERROR_RESPONSES,
)
async def get_course(course_id: uuid.UUID, db: DbDep, user: UserDep) -> CourseOut:
    return await CourseService(db, user).get(course_id)


@router.patch("/{course_id}", response_model=CourseOut, summary="Update a course", responses=ERROR_RESPONSES, dependencies=WRITE)
async def update_course(course_id: uuid.UUID, data: CourseUpdate, db: DbDep, user: UserDep) -> CourseOut:
    return await CourseService(db, user).update(course_id, data)


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a course",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def delete_course(course_id: uuid.UUID, db: DbDep, user: UserDep) -> Response:
    await CourseService(db, user).delete(course_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
