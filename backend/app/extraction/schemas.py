from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: str = Field(description="Question label as printed, e.g. '1', '2(a)', '3(b)'")
    text: str = Field(description="Full question text, verbatim, without the marks annotation")
    marks: float = Field(description="Marks allocated; 0 if not stated")


class ExtractedQuestions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[ExtractedQuestion]
    notes: str = Field(description="Ambiguities or unreadable parts; empty string if none")


class ExtractedTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(description="Short code such as 'T-01'")
    title: str = Field(description="Topic title as written in the syllabus")


class ExtractedTopics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topics: list[ExtractedTopic]
    notes: str
