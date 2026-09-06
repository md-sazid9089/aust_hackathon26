from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.db.enums import ArtefactKind, BloomLevel, ExtractionStatus, TextLang
from app.schemas import ApiModel


class ArtefactCounts(ApiModel):
    questions: int = 0
    topics: int = 0
    students: int = 0
    criteria: int = 0
    answers: int = 0


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


# --- marks sheet -----------------------------------------------------------
class MarksQuestionOut(ApiModel):
    number: str
    max: float
    co_code: str | None = None


class MarksRowOut(ApiModel):
    student_anon_id: str
    scores: dict[str, float]


class MarksSheetOut(ApiModel):
    students: int
    questions: list[MarksQuestionOut]
    rows: list[MarksRowOut]


# --- rubric ----------------------------------------------------------------
class RubricLevel(ApiModel):
    label: str = Field(min_length=1, max_length=40)
    score: float = Field(ge=0, le=1000)
    descriptor: str = Field(max_length=2000)


class RubricCriterionIn(ApiModel):
    id: uuid.UUID | None = None
    code: str = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1, max_length=1000)
    max_score: float = Field(gt=0, le=1000)
    levels: list[RubricLevel] = Field(default_factory=list, max_length=12)

    @field_validator("code")
    @classmethod
    def _norm(cls, v: str) -> str:
        return "".join(v.upper().split())


class RubricCriterionOut(RubricCriterionIn):
    id: uuid.UUID  # type: ignore[assignment]


# --- answer set --------------------------------------------------------------
class GraderScore(ApiModel):
    grader_label: str = Field(min_length=1, max_length=40)
    criterion_code: str = Field(min_length=1, max_length=20)
    score: float = Field(ge=0, le=1000)

    @field_validator("criterion_code")
    @classmethod
    def _norm(cls, v: str) -> str:
        return "".join(v.upper().split())


class AnswerIn(ApiModel):
    id: uuid.UUID | None = None
    student_anon_id: str = Field(min_length=1, max_length=40)
    question_ref: str | None = Field(None, max_length=20)
    text: str = Field(min_length=1, max_length=20_000)
    grader_scores: list[GraderScore] = Field(default_factory=list, max_length=200)


class AnswerOut(AnswerIn):
    id: uuid.UUID  # type: ignore[assignment]


class QuestionIn(ApiModel):
    id: uuid.UUID | None = None
    number: str = Field(min_length=1, max_length=20, examples=["3(b)"])
    text: str = Field(min_length=3, max_length=5000)
    marks: float = Field(ge=0, le=1000)

    @field_validator("number")
    @classmethod
    def _norm(cls, v: str) -> str:
        v = "".join(v.split())
        if not v:
            raise ValueError("number must not be blank")
        if not re.fullmatch(r"[A-Za-z0-9().\-]+", v):
            raise ValueError("number may only contain letters, digits, parentheses, dots and hyphens")
        return v


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
