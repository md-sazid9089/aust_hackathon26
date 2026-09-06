from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas import ApiModel


class CourseCreate(ApiModel):
    code: str = Field(min_length=2, max_length=20, examples=["CSE 3103"])
    title: str = Field(min_length=2, max_length=200)
    term: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=4000)

    @field_validator("code")
    @classmethod
    def _normalise_code(cls, v: str) -> str:
        v = " ".join(v.strip().upper().split())
        if len(v) < 2:
            raise ValueError("code too short")
        return v


class CourseUpdate(ApiModel):
    code: str | None = Field(None, min_length=2, max_length=20)
    title: str | None = Field(None, min_length=2, max_length=200)
    term: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=4000)

    @field_validator("code")
    @classmethod
    def _normalise_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = " ".join(v.strip().upper().split())
        if len(v) < 2:
            raise ValueError("code too short")
        return v


class CourseCounts(ApiModel):
    artefacts: int = 0
    runs: int = 0
    outcomes: int = 0


class CourseOut(ApiModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    code: str
    title: str
    term: str | None
    description: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime
    counts: CourseCounts | None = None
