from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, File, Form, Query, Response, UploadFile, status

from app.artefacts.schemas import ArtefactOut, ArtefactTextOut, QuestionCoMapIn, QuestionIn, QuestionOut
from app.artefacts.service import ArtefactService
from app.db.enums import ArtefactKind, ExtractionStatus, Permission
from app.deps import DbDep, UserDep, require_permission, uploads_rate_limit
from app.schemas import ERROR_RESPONSES

router = APIRouter(tags=["artefacts"])
WRITE = [Depends(require_permission(Permission.artefacts_write))]


@router.post(
    "/courses/{course_id}/artefacts",
    response_model=ArtefactOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload or paste an artefact",
    description=(
        "Multipart form. Provide exactly one of `file` (pdf/docx/txt/md, ≤ MAX_UPLOAD_MB) or `text`. "
        "File type is verified by magic bytes. Extraction runs in the background; poll the artefact "
        "until `status` is `done` or `failed`. Supported kinds in this build: `question_paper`, `syllabus`."
    ),
    responses={**ERROR_RESPONSES, 413: {"description": "FILE_TOO_LARGE"}, 415: {"description": "UNSUPPORTED_FILE_TYPE"}},
    dependencies=[Depends(require_permission(Permission.artefacts_write)), Depends(uploads_rate_limit)],
)
async def upload_artefact(
    course_id: uuid.UUID,
    db: DbDep,
    user: UserDep,
    kind: Annotated[ArtefactKind, Form()],
    label: Annotated[str, Form(min_length=1, max_length=200)],
    year: Annotated[int | None, Form(ge=1990, le=2100)] = None,
    term: Annotated[str | None, Form(max_length=50)] = None,
    declared_total_marks: Annotated[float | None, Form(ge=0, le=1000)] = None,
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form(max_length=200_000)] = None,
) -> ArtefactOut:
    return await ArtefactService(db, user).create(
        course_id, kind=kind, label=label, year=year, term=term,
        declared_total_marks=declared_total_marks, file=file, text=text,
    )


@router.get("/courses/{course_id}/artefacts", response_model=list[ArtefactOut], summary="List course artefacts", responses=ERROR_RESPONSES)
async def list_artefacts(
    course_id: uuid.UUID,
    db: DbDep,
    user: UserDep,
    kind: Annotated[ArtefactKind | None, Query()] = None,
    status_: Annotated[ExtractionStatus | None, Query(alias="status")] = None,
) -> list[ArtefactOut]:
    return await ArtefactService(db, user).list(course_id, kind=kind, status=status_)


@router.get("/artefacts/{artefact_id}", response_model=ArtefactOut, summary="Get artefact status", responses=ERROR_RESPONSES)
async def get_artefact(artefact_id: uuid.UUID, db: DbDep, user: UserDep) -> ArtefactOut:
    return await ArtefactService(db, user).get(artefact_id)


@router.get("/artefacts/{artefact_id}/text", response_model=ArtefactTextOut, summary="Extracted plain text", responses=ERROR_RESPONSES)
async def get_artefact_text(artefact_id: uuid.UUID, db: DbDep, user: UserDep) -> ArtefactTextOut:
    return ArtefactTextOut.model_validate(await ArtefactService(db, user).get_text(artefact_id))


@router.delete(
    "/artefacts/{artefact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an artefact",
    description="`409 ARTEFACT_IN_USE` if a completed run references it.",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def delete_artefact(artefact_id: uuid.UUID, db: DbDep, user: UserDep) -> Response:
    await ArtefactService(db, user).delete(artefact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/artefacts/{artefact_id}/reextract",
    response_model=ArtefactOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Re-run extraction",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def reextract(artefact_id: uuid.UUID, db: DbDep, user: UserDep) -> ArtefactOut:
    return await ArtefactService(db, user).reextract(artefact_id)


@router.get("/artefacts/{artefact_id}/questions", response_model=list[QuestionOut], summary="Extracted questions", responses=ERROR_RESPONSES)
async def questions(artefact_id: uuid.UUID, db: DbDep, user: UserDep) -> list[QuestionOut]:
    return await ArtefactService(db, user).questions(artefact_id)


@router.put(
    "/artefacts/{artefact_id}/questions",
    response_model=list[QuestionOut],
    summary="Confirm/edit extracted questions (replace-all)",
    description="The faculty confirmation step. Items without `id` are inserted; omitted existing questions are deleted.",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def replace_questions(
    artefact_id: uuid.UUID, db: DbDep, user: UserDep, items: list[QuestionIn] = Body(max_length=200)
) -> list[QuestionOut]:
    return await ArtefactService(db, user).replace_questions(artefact_id, items)


@router.put(
    "/artefacts/{artefact_id}/questions/co-map",
    response_model=list[QuestionOut],
    summary="Set faculty question→CO mapping",
    description="Faculty-confirmed mapping (source=faculty) overrides AI mapping for the listed questions.",
    responses=ERROR_RESPONSES,
    dependencies=WRITE,
)
async def set_co_map(
    artefact_id: uuid.UUID, db: DbDep, user: UserDep, items: list[QuestionCoMapIn] = Body(max_length=200)
) -> list[QuestionOut]:
    return await ArtefactService(db, user).set_co_map(artefact_id, items)
