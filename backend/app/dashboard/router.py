"""F-023 cross-course dashboard for the signed-in faculty member."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import func, select

from app.db.enums import FindingStatus, RunModule, RunStatus
from app.db.models import Course, Finding, Run
from app.deps import DbDep, UserDep
from app.schemas import ERROR_RESPONSES, ApiModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

FINISHED = (RunStatus.completed, RunStatus.partial)


class LastAudit(ApiModel):
    run_id: uuid.UUID
    open_findings: int
    coverage_pct: float


class LastAttainment(ApiModel):
    run_id: uuid.UUID
    cos_met: int
    cos_total: int


class DashboardCourse(ApiModel):
    course_id: uuid.UUID
    code: str
    title: str
    last_exam_audit: LastAudit | None = None
    last_attainment: LastAttainment | None = None


class DashboardTotals(ApiModel):
    runs: int
    accepted_findings: int
    dismissed_findings: int


class DashboardOut(ApiModel):
    courses: list[DashboardCourse]
    totals: DashboardTotals


async def _last_run(db, course_id: uuid.UUID, module: RunModule) -> Run | None:  # noqa: ANN001
    stmt = select(Run).where(Run.course_id == course_id, Run.module == module, Run.status.in_(FINISHED)).order_by(Run.finished_at.desc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


@router.get("/summary", response_model=DashboardOut, summary="Per-course latest results + totals", responses=ERROR_RESPONSES)
async def summary(db: DbDep, user: UserDep) -> DashboardOut:
    courses = list((await db.execute(select(Course).where(Course.owner_id == user.id, Course.deleted_at.is_(None)).order_by(Course.created_at.desc()))).scalars())
    out: list[DashboardCourse] = []
    for c in courses:
        item = DashboardCourse(course_id=c.id, code=c.code, title=c.title)
        audit = await _last_run(db, c.id, RunModule.exam_audit)
        if audit is not None:
            open_n = (await db.execute(select(func.count()).where(Finding.run_id == audit.id, Finding.status == FindingStatus.open))).scalar_one()
            item.last_exam_audit = LastAudit(run_id=audit.id, open_findings=open_n, coverage_pct=float((audit.summary or {}).get("coverage_pct", 0)))
        att = await _last_run(db, c.id, RunModule.attainment)
        if att is not None:
            s = att.summary or {}
            item.last_attainment = LastAttainment(run_id=att.id, cos_met=int(s.get("cos_met", 0)), cos_total=int(s.get("cos_total", 0)))
        out.append(item)
    runs = (await db.execute(select(func.count()).where(Run.owner_id == user.id))).scalar_one()
    accepted = (await db.execute(select(func.count()).where(Finding.owner_id == user.id, Finding.status == FindingStatus.accepted))).scalar_one()
    dismissed = (await db.execute(select(func.count()).where(Finding.owner_id == user.id, Finding.status == FindingStatus.dismissed))).scalar_one()
    return DashboardOut(courses=out, totals=DashboardTotals(runs=runs, accepted_findings=accepted, dismissed_findings=dismissed))
