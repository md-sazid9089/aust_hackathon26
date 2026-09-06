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


@router.get("/summary", response_model=DashboardOut, summary="Per-course latest results + totals", responses=ERROR_RESPONSES)
async def summary(db: DbDep, user: UserDep) -> DashboardOut:
    courses = list((await db.execute(select(Course).where(Course.owner_id == user.id, Course.deleted_at.is_(None)).order_by(Course.created_at.desc()))).scalars())
    if not courses:
        return DashboardOut(courses=[], totals=DashboardTotals(runs=0, accepted_findings=0, dismissed_findings=0))
    course_ids = [c.id for c in courses]

    # One query for every finished exam_audit/attainment run; pick the latest per (course, module) in Python.
    run_rows = list((await db.execute(
        select(Run)
        .where(Run.course_id.in_(course_ids), Run.module.in_((RunModule.exam_audit, RunModule.attainment)), Run.status.in_(FINISHED))
        .order_by(Run.finished_at.desc())
    )).scalars())
    latest: dict[tuple[uuid.UUID, RunModule], Run] = {}
    for r in run_rows:
        latest.setdefault((r.course_id, r.module), r)

    # One grouped query for open-finding counts across the chosen audit runs.
    audit_ids = [r.id for (_, m), r in latest.items() if m == RunModule.exam_audit]
    open_by_run: dict[uuid.UUID, int] = {}
    if audit_ids:
        open_by_run = {
            rid: n
            for rid, n in (await db.execute(
                select(Finding.run_id, func.count())
                .where(Finding.run_id.in_(audit_ids), Finding.status == FindingStatus.open)
                .group_by(Finding.run_id)
            )).all()
        }

    out: list[DashboardCourse] = []
    for c in courses:
        item = DashboardCourse(course_id=c.id, code=c.code, title=c.title)
        audit = latest.get((c.id, RunModule.exam_audit))
        if audit is not None:
            item.last_exam_audit = LastAudit(run_id=audit.id, open_findings=open_by_run.get(audit.id, 0), coverage_pct=float((audit.summary or {}).get("coverage_pct", 0)))
        att = latest.get((c.id, RunModule.attainment))
        if att is not None:
            s = att.summary or {}
            item.last_attainment = LastAttainment(run_id=att.id, cos_met=int(s.get("cos_met", 0)), cos_total=int(s.get("cos_total", 0)))
        out.append(item)

    runs = (await db.execute(select(func.count()).where(Run.owner_id == user.id))).scalar_one()
    finding_counts = {
        status: n
        for status, n in (await db.execute(
            select(Finding.status, func.count())
            .where(Finding.owner_id == user.id, Finding.status.in_((FindingStatus.accepted, FindingStatus.dismissed)))
            .group_by(Finding.status)
        )).all()
    }
    totals = DashboardTotals(
        runs=runs,
        accepted_findings=finding_counts.get(FindingStatus.accepted, 0),
        dismissed_findings=finding_counts.get(FindingStatus.dismissed, 0),
    )
    return DashboardOut(courses=out, totals=totals)
