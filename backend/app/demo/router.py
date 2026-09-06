from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.demo.service import seed_demo
from app.deps import DbDep, UserDep
from app.schemas import ERROR_RESPONSES, ApiModel

router = APIRouter(prefix="/demo", tags=["demo"])


class SeedOut(ApiModel):
    course_id: uuid.UUID
    created: bool
    note: str = "Demo dataset (clearly labelled sample data, not real university records)."


@router.post(
    "/seed",
    response_model=SeedOut,
    summary="Create the demo course for the current user",
    description=(
        "Loads the sample CSE 3103 dataset (6 COs, CO→PO map, 14 topics, 2 past papers, 1 flawed draft paper) "
        "into the caller's workspace. Idempotent: returns the existing demo course if already seeded."
    ),
    responses=ERROR_RESPONSES,
)
async def seed(db: DbDep, user: UserDep) -> SeedOut:
    course, created = await seed_demo(db, user)
    return SeedOut(course_id=course.id, created=created)
