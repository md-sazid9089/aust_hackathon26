from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select

from app.db.enums import FindingSeverity, FindingType, TargetKind
from app.db.models import Finding, Run, RunEvent, utcnow
from app.db.session import session_scope
from app.logging import get_logger

log = get_logger(__name__)


@dataclass
class FindingDraft:
    type: FindingType
    severity: FindingSeverity
    title: str
    rationale: str
    evidence_snippet: str | None = None
    target_kind: TargetKind = TargetKind.none
    target_id: uuid.UUID | None = None
    target_label: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_model(self, run: Run) -> Finding:
        return Finding(
            run_id=run.id, owner_id=run.owner_id, type=self.type, severity=self.severity, title=self.title,
            rationale=self.rationale, evidence_snippet=self.evidence_snippet, target_kind=self.target_kind,
            target_id=self.target_id, target_label=self.target_label, payload=self.payload,
            provenance=self.provenance,
        )


class StageFailed(Exception):
    """A required stage failed; the run cannot produce results."""


@dataclass
class RunContext:
    """Handle given to a module pipeline. Each write happens in its own short transaction."""

    run_id: uuid.UUID
    owner_id: uuid.UUID
    course_id: uuid.UUID
    params: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    model_used: str | None = None
    prompt_versions: dict[str, str] = field(default_factory=dict)

    async def emit(self, stage: str, message: str, pct: int | None, level: str = "info") -> None:
        async with session_scope() as db:
            run = await db.get(Run, self.run_id)
            if run is None:
                return
            seq = (await db.execute(select(func.coalesce(func.max(RunEvent.seq), -1)).where(RunEvent.run_id == self.run_id))).scalar_one() + 1
            db.add(RunEvent(run_id=self.run_id, seq=seq, stage=stage, message=message, pct=pct, level=level))
            run.current_stage = stage
            if pct is not None:
                run.progress_pct = max(run.progress_pct, min(100, pct))
        log.info("run.stage", run_id=str(self.run_id), stage=stage, pct=pct, level=level)

    async def warn(self, stage: str, message: str) -> None:
        self.warnings.append(message)
        await self.emit(stage, message, pct=None, level="warning")


async def append_terminal_event(run_id: uuid.UUID, status: str, message: str) -> None:
    async with session_scope() as db:
        seq = (await db.execute(select(func.coalesce(func.max(RunEvent.seq), -1)).where(RunEvent.run_id == run_id))).scalar_one() + 1
        db.add(RunEvent(run_id=run_id, seq=seq, stage="done", message=message, pct=100, level="info" if status != "failed" else "error", at=utcnow()))
