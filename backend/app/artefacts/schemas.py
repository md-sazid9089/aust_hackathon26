from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.db.enums import ArtefactKind, BloomLevel, ExtractionStatus, TextLang
from app.schemas import ApiModel


class ArtefactCounts(ApiModel):
    questions: int = 0
    topics: int = 0


class ArtefactOut(ApiModel):
    id: uuid.UUID
    course_id: uuid.UUID
    kind: ArtefactKind
    label: str
    year: int | None
    term: str | None
    mime: str | None
    size_bytes: int | None
    lang: TextLang
    status: ExtractionStatus
    error: str | None
    declared_total_marks: float | None
    created_at: datetime
    updated_at: datetime
    counts: ArtefactCounts | None = None


class ArtefactTextOut(ApiModel):
    id: uuid.UUID
    extracted_text: str | None


class QuestionIn(ApiModel):
    id: uuid.UUID | None = None
    number: str = Field(min_length=1, max_length=20, examples=["3(b)"])
    text: str = Field(min_length=3, max_length=5000)
    marks: float = Field(ge=0, le=1000)

    @field_validator("number")
    @classmethod
    def _norm(cls, v: str) -> str:
        return "".join(v.split())


class QuestionOut(ApiModel):
    id: uuid.UUID
    artefact_id: uuid.UUID
    number: str
    text: str
    marks: float
    bloom_level: BloomLevel | None
    bloom_source: str | None
    co_ids: list[uuid.UUID] = Field(default_factory=list)
    topic_ids: list[uuid.UUID] = Field(default_factory=list)
    sort_order: int


class QuestionCoMapIn(ApiModel):
    question_id: uuid.UUID
    co_ids: list[uuid.UUID] = Field(max_length=20)
