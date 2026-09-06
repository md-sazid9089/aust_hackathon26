from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import BloomLevel

DuplicateLevel = Literal["identical", "paraphrase", "same_concept", "distinct"]
# Levels that count as a repeat for the faculty (same task; a memorised answer would score).
DUPLICATE_LEVELS: frozenset[str] = frozenset({"identical", "paraphrase"})


class QuestionMapItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: str
    co_codes: list[str] = Field(description="Course outcome codes this question assesses (at most 2); [] if none fit")
    topic_codes: list[str] = Field(description="Syllabus topic codes (at most 2); [] if none fit")
    bloom_level: BloomLevel
    confidence: float = Field(ge=0, le=1)
    evidence_quote: str = Field(description="Verbatim phrase from the question (the task verb and its object) that decided the Bloom level")
    rationale: str


class MapAndBloomOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[QuestionMapItem]


class DupConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_number: str
    other_question_id: str
    level: DuplicateLevel = Field(description="identical | paraphrase | same_concept | distinct (see definitions)")
    confidence: float = Field(ge=0, le=1)
    evidence_draft: str = Field(description="Verbatim decisive phrase from the draft question")
    evidence_other: str = Field(description="Verbatim decisive phrase from the other question")
    rationale: str

    @property
    def is_duplicate(self) -> bool:
        return self.level in DUPLICATE_LEVELS


class ConfirmDuplicatesOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[DupConfirm]
