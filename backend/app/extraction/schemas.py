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


class ExtractedLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="Band label, usually the score, e.g. '4'")
    score: float
    descriptor: str


class ExtractedCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(description="Criterion code as printed, e.g. 'R1', 'C2'; invent R1.. only if none")
    text: str = Field(description="Criterion title/description, verbatim")
    max_score: float = Field(description="Maximum marks for this criterion")
    levels: list[ExtractedLevel] = Field(description="Performance bands with score and descriptor; empty if none")


class ExtractedRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criteria: list[ExtractedCriterion]
    notes: str


class ExtractedGraderScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grader_label: str
    criterion_code: str
    score: float


class ExtractedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    student_anon_id: str = Field(description="Student identifier exactly as given (never a name)")
    question_ref: str = Field(description="Question label the answer addresses; empty string if unknown")
    text: str = Field(description="The student's answer, verbatim")
    grader_scores: list[ExtractedGraderScore] = Field(description="Every grader's score per criterion as stated")


class ExtractedAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[ExtractedAnswer]
    notes: str
