from __future__ import annotations

import uuid

from pydantic import Field, field_validator

from app.db.enums import BloomLevel
from app.schemas import ApiModel


def _norm_code(v: str) -> str:
    v = " ".join(v.strip().upper().split())
    if not v:
        raise ValueError("code must not be empty")
    return v


class ProgramOutcomeOut(ApiModel):
    id: uuid.UUID
    code: str
    text: str
    sort_order: int


class CourseOutcomeIn(ApiModel):
    id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=20, examples=["CO1"])
    text: str = Field(min_length=3, max_length=2000)
    bloom_level: BloomLevel | None = None
    weight: float = Field(1.0, gt=0, le=1000)

    _norm = field_validator("code")(classmethod(lambda cls, v: _norm_code(v)))


class CourseOutcomeOut(ApiModel):
    id: uuid.UUID
    course_id: uuid.UUID
    code: str
    text: str
    bloom_level: BloomLevel | None
    weight: float
    sort_order: int


class CoPoCell(ApiModel):
    co_id: uuid.UUID
    po_id: uuid.UUID
    strength: int = Field(ge=0, le=3)


class TopicIn(ApiModel):
    id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=20, examples=["T-01"])
    title: str = Field(min_length=2, max_length=500)

    _norm = field_validator("code")(classmethod(lambda cls, v: _norm_code(v)))


class TopicOut(ApiModel):
    id: uuid.UUID
    course_id: uuid.UUID
    code: str
    title: str
    source_artefact_id: uuid.UUID | None
    sort_order: int
