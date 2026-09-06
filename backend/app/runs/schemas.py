from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from app.db.enums import FindingSeverity, FindingStatus, FindingType, RunModule, RunStatus, TargetKind
from app.schemas import ApiModel


class ExamAuditInputs(ApiModel):
    draft_artefact_id: uuid.UUID
    past_artefact_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _distinct(self) -> ExamAuditInputs:
        if self.draft_artefact_id in self.past_artefact_ids:
            raise ValueError("draft paper cannot also be a past paper")
        if len(set(self.past_artefact_ids)) != len(self.past_artefact_ids):
            raise ValueError("past_artefact_ids must be distinct")
        return self


class ExamAuditParams(ApiModel):
    dup_threshold: float = Field(0.80, ge=0.5, le=0.99)
    overweight_factor: float = Field(1.5, ge=1.0, le=5.0)
    bloom_lower_cap: float = Field(0.40, ge=0.0, le=1.0)
    bloom_higher_floor: float = Field(0.30, ge=0.0, le=1.0)
    fairness_max_single_share: float = Field(0.30, ge=0.05, le=1.0)


class AttainmentInputs(ApiModel):
    marks_artefact_id: uuid.UUID
    paper_artefact_id: uuid.UUID
    threshold: float = Field(0.60, ge=0.1, le=1.0, description="Fraction of a CO's marks a student must score to attain it")


class AttainmentParams(ApiModel):
    target_pct: float = Field(60.0, ge=1, le=100, description="% of students who must attain each CO/PO")


class SyllabusCheckInputs(ApiModel):
    syllabus_artefact_id: uuid.UUID
    compare_course_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def _distinct(self) -> SyllabusCheckInputs:
        if len(set(self.compare_course_ids)) != len(self.compare_course_ids):
            raise ValueError("compare_course_ids must be distinct")
        return self


class SyllabusCheckParams(ApiModel):
    candidate_threshold: float = Field(0.45, ge=0.1, le=0.95)
    overlap_threshold: float = Field(0.70, ge=0.3, le=0.99)
    max_pairs: int = Field(40, ge=5, le=200)


class CalibrationInputs(ApiModel):
    rubric_artefact_id: uuid.UUID
    answer_set_artefact_id: uuid.UUID


class CalibrationParams(ApiModel):
    divergence_share: float = Field(0.25, ge=0.05, le=1.0)
    flag_criterion_mean: float = Field(1.0, ge=0.1, le=100)
    prescore_batch: int = Field(6, ge=1, le=20)


MODULE_SCHEMAS: dict[RunModule, tuple[type[ApiModel], type[ApiModel]]] = {
    RunModule.exam_audit: (ExamAuditInputs, ExamAuditParams),
    RunModule.attainment: (AttainmentInputs, AttainmentParams),
    RunModule.syllabus_check: (SyllabusCheckInputs, SyllabusCheckParams),
    RunModule.calibration: (CalibrationInputs, CalibrationParams),
}


def input_roles(module: RunModule, inputs: ApiModel) -> list[tuple[uuid.UUID, str]]:
    """(artefact_id, run_inputs.role) pairs a module consumes."""
    if isinstance(inputs, ExamAuditInputs):
        return [(inputs.draft_artefact_id, "draft")] + [(a, "past") for a in inputs.past_artefact_ids]
    if isinstance(inputs, AttainmentInputs):
        return [(inputs.marks_artefact_id, "marks"), (inputs.paper_artefact_id, "paper")]
    if isinstance(inputs, SyllabusCheckInputs):
        return [(inputs.syllabus_artefact_id, "syllabus")]
    if isinstance(inputs, CalibrationInputs):
        return [(inputs.rubric_artefact_id, "rubric"), (inputs.answer_set_artefact_id, "answer_set")]
    return []


class RunCreate(ApiModel):
    module: RunModule
    inputs: dict[str, Any] = Field(
        description=(
            "Module-specific. exam_audit: {draft_artefact_id, past_artefact_ids[]} · "
            "attainment: {marks_artefact_id, paper_artefact_id, threshold} · "
            "syllabus_check: {syllabus_artefact_id, compare_course_ids[]} · "
            "calibration: {rubric_artefact_id, answer_set_artefact_id}"
        )
    )
    params: dict[str, Any] = Field(default_factory=dict)


class RunOut(ApiModel):
    id: uuid.UUID
    course_id: uuid.UUID
    module: RunModule
    status: RunStatus
    progress_pct: int
    current_stage: str | None
    error: str | None
    inputs: dict[str, Any]
    params: dict[str, Any]
    summary: dict[str, Any] | None
    model: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class RunEventOut(ApiModel):
    seq: int
    stage: str
    message: str | None
    pct: int | None
    level: str
    at: datetime


class FindingOut(ApiModel):
    id: uuid.UUID
    run_id: uuid.UUID
    type: FindingType
    severity: FindingSeverity
    title: str
    rationale: str
    evidence_snippet: str | None
    target_kind: TargetKind
    target_id: uuid.UUID | None
    target_label: str | None
    payload: dict[str, Any]
    provenance: dict[str, Any]
    status: FindingStatus
    decided_at: datetime | None
    created_at: datetime


class FindingPatch(ApiModel):
    status: FindingStatus


class CompareOut(ApiModel):
    resolved: list[FindingOut]
    new: list[FindingOut]
    persisting: list[dict[str, FindingOut]]


class SuggestIn(ApiModel):
    co_ids: list[uuid.UUID] = Field(default_factory=list, max_length=20)


class AttainmentCoOut(ApiModel):
    co_id: uuid.UUID
    co_code: str
    attained_pct: float
    students: int
    target_pct: float
    met: bool


class AttainmentPoOut(ApiModel):
    po_id: uuid.UUID
    po_code: str
    attained_pct: float
    met: bool


class AttainmentOut(ApiModel):
    threshold: float
    cos: list[AttainmentCoOut]
    pos: list[AttainmentPoOut]


class PrescoreOut(ApiModel):
    answer_id: uuid.UUID
    student_anon_id: str
    criterion_code: str
    ai_score: float
    rationale: str
    grader_scores: dict[str, float]
