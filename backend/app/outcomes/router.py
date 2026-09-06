from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Depends

from app.db.enums import Permission
from app.deps import DbDep, UserDep, require_permission
from app.outcomes.schemas import CoPoCell, CourseOutcomeIn, CourseOutcomeOut, ProgramOutcomeOut, TopicIn, TopicOut
from app.outcomes.service import OutcomeService
from app.schemas import ERROR_RESPONSES

router = APIRouter(tags=["outcomes"])
WRITE = [Depends(require_permission(Permission.courses_write))]


@router.get("/program-outcomes", response_model=list[ProgramOutcomeOut], summary="Global programme outcomes (PO1–PO12)")
async def program_outcomes(db: DbDep, user: UserDep) -> list[ProgramOutcomeOut]:
    return await OutcomeService(db, user).program_outcomes()


@router.get("/courses/{course_id}/outcomes", response_model=list[CourseOutcomeOut], summary="List course outcomes", responses=ERROR_RESPONSES)
async def list_outcomes(course_id: uuid.UUID, db: DbDep, user: UserDep) -> list[CourseOutcomeOut]:
    return await OutcomeService(db, user).list_outcomes(course_id)


@router.put(
    "/courses/{course_id}/outcomes",
    response_model=list[CourseOutcomeOut],
    summary="Replace all course outcomes",
    description="Replace-all in one transaction. Omitted existing COs are deleted; `409 OUTCOME_IN_USE` if a deleted CO is mapped to questions.",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def replace_outcomes(
    course_id: uuid.UUID, db: DbDep, user: UserDep, items: list[CourseOutcomeIn] = Body(max_length=50)
) -> list[CourseOutcomeOut]:
    return await OutcomeService(db, user).replace_outcomes(course_id, items)


@router.get("/courses/{course_id}/co-po-map", response_model=list[CoPoCell], summary="CO→PO map", responses=ERROR_RESPONSES)
async def co_po_map(course_id: uuid.UUID, db: DbDep, user: UserDep) -> list[CoPoCell]:
    return await OutcomeService(db, user).co_po_map(course_id)


@router.put("/courses/{course_id}/co-po-map", response_model=list[CoPoCell], summary="Replace CO→PO map", responses=ERROR_RESPONSES, dependencies=WRITE)
async def replace_co_po_map(
    course_id: uuid.UUID, db: DbDep, user: UserDep, cells: list[CoPoCell] = Body(max_length=600)
) -> list[CoPoCell]:
    return await OutcomeService(db, user).replace_co_po_map(course_id, cells)


@router.get("/courses/{course_id}/topics", response_model=list[TopicOut], summary="List syllabus topics", responses=ERROR_RESPONSES)
async def topics(course_id: uuid.UUID, db: DbDep, user: UserDep) -> list[TopicOut]:
    return await OutcomeService(db, user).topics(course_id)


@router.put(
    "/courses/{course_id}/topics",
    response_model=list[TopicOut],
    summary="Replace all syllabus topics",
    description="Used to confirm/edit topics after syllabus extraction.",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def replace_topics(
    course_id: uuid.UUID, db: DbDep, user: UserDep, items: list[TopicIn] = Body(max_length=200)
) -> list[TopicOut]:
    return await OutcomeService(db, user).replace_topics(course_id, items)
