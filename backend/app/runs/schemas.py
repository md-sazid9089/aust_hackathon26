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


class RunCreate(ApiModel):
    module: RunModule
    inputs: dict[str, Any] = Field(description="Module-specific; exam_audit: {draft_artefact_id, past_artefact_ids[]}")
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
