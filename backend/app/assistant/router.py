from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import TypeAdapter, ValidationError

from app.assistant.schemas import ChatMessage, ChatResponse
from app.assistant.service import AssistantService
from app.assistant.tools import Attachment
from app.deps import DbDep, RateLimiter, SettingsDep, UserDep
from app.errors import ApiError
from app.schemas import ERROR_RESPONSES

router = APIRouter(prefix="/assistant", tags=["assistant"])
assistant_rate_limit = RateLimiter(limit=30)
_history_adapter = TypeAdapter(list[ChatMessage])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with the in-app assistant",
    description=(
        "Multipart form. `message` (required), `history` (JSON array of `{role, content}`, last 12 kept), "
        "`course_id` (course the user is currently viewing, optional) and an optional `file` (pdf/docx/txt/md). "
        "The assistant answers product questions and can perform any faculty action (create courses, upload the "
        "attached file as an artefact, run an exam audit, accept/dismiss findings, export, seed demo). Actions run with "
        "the caller's own permissions and are reported in `actions`; `navigate` is a route the UI may open."
    ),
    responses={**ERROR_RESPONSES, 503: {"description": "ASSISTANT_UNAVAILABLE"}},
    dependencies=[Depends(assistant_rate_limit)],
)
async def chat(
    db: DbDep,
    user: UserDep,
    settings: SettingsDep,
    message: Annotated[str, Form(min_length=1, max_length=8000)],
    history: Annotated[str | None, Form(max_length=60_000)] = None,
    course_id: Annotated[uuid.UUID | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
) -> ChatResponse:
    msgs: list[ChatMessage] = []
    if history:
        try:
            msgs = _history_adapter.validate_python(json.loads(history))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ApiError("VALIDATION_ERROR", 422, "history must be a JSON array of {role, content}") from exc
    attachment: Attachment | None = None
    if file is not None and file.filename:
        data = await file.read(settings.max_upload_bytes + 1)
        if len(data) > settings.max_upload_bytes:
            raise ApiError("FILE_TOO_LARGE", 413, f"File exceeds {settings.max_upload_mb} MB")
        if data:
            attachment = Attachment(filename=file.filename, data=data)
    return await AssistantService(db, user).chat(message=message, history=msgs, current_course_id=course_id, attachment=attachment)
