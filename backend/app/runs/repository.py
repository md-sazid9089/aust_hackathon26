from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import FindingSeverity, FindingStatus, FindingType, RunModule, RunStatus
from app.db.models import Finding, Run, RunEvent


class RunRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, run_id: uuid.UUID) -> Run | None:
        return await self.db.get(Run, run_id)

    async def by_idempotency(self, owner_id: uuid.UUID, key: str) -> Run | None:
        stmt = select(Run).where(Run.owner_id == owner_id, Run.idempotency_key == key)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_course(
        self, course_id: uuid.UUID, *, module: RunModule | None, status: RunStatus | None, offset: int, limit: int
    ) -> tuple[list[Run], int]:
        stmt = select(Run).where(Run.course_id == course_id)
        if module:
            stmt = stmt.where(Run.module == module)
        if status:
            stmt = stmt.where(Run.status == status)
        total = (await self.db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
        rows = (await self.db.execute(stmt.order_by(Run.created_at.desc()).offset(offset).limit(limit))).scalars().all()
        return list(rows), total

    async def events(self, run_id: uuid.UUID, after_seq: int = -1) -> list[RunEvent]:
        stmt = select(RunEvent).where(RunEvent.run_id == run_id, RunEvent.seq > after_seq).order_by(RunEvent.seq)
        return list((await self.db.execute(stmt)).scalars().all())

    async def findings(
        self, run_id: uuid.UUID, *, type_: FindingType | None, status: FindingStatus | None, severity: FindingSeverity | None
    ) -> list[Finding]:
        stmt = select(Finding).where(Finding.run_id == run_id)
        if type_:
            stmt = stmt.where(Finding.type == type_)
        if status:
            stmt = stmt.where(Finding.status == status)
        if severity:
            stmt = stmt.where(Finding.severity == severity)
        rows = list((await self.db.execute(stmt.order_by(Finding.created_at))).scalars().all())
        order = {"high": 0, "medium": 1, "low": 2, "info": 3}
        rows.sort(key=lambda f: (order.get(f.severity.value, 9), f.created_at))
        return rows

    async def finding(self, finding_id: uuid.UUID) -> Finding | None:
        return await self.db.get(Finding, finding_id)

    async def sweep_stale(self) -> int:
        """On startup mark runs that were in flight before a restart as failed."""
        stmt = select(Run).where(Run.status.in_([RunStatus.queued, RunStatus.analyzing]))
        rows = list((await self.db.execute(stmt)).scalars().all())
        for r in rows:
            r.status = RunStatus.failed
            r.error = "Server restarted while the run was in progress"
        return len(rows)
