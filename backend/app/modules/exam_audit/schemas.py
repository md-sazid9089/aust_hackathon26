from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import BloomLevel


class QuestionMapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: str
    co_codes: list[str] = Field(description="Course outcome codes this question assesses; [] if none fit")
    topic_codes: list[str] = Field(description="Syllabus topic codes; [] if none fit")
    bloom_level: BloomLevel
    confidence: float = Field(ge=0, le=1)
    rationale: str


class MapAndBloomOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[QuestionMapItem]


class DupConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_number: str
    other_question_id: str
    is_duplicate: bool
    rationale: str


class ConfirmDuplicatesOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[DupConfirm]
