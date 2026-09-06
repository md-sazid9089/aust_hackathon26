"""CF-001 admin panel: read-only oversight (users, runs, LLM usage, department views) + demo reset (F-034).

Admins cannot edit findings (SEC-009) — enforced by `findings_decide` permission on the runs router.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import Field
from sqlalchemy import delete, func, select

from app.auth.passwords import hash_password
from app.db.enums import AppRole, FindingStatus, FindingType, Permission, RunModule, RunStatus
from app.db.models import Course, Finding, Profile, Run, UsageLog
from app.demo.service import seed_demo
from app.deps import DbDep, UserDep, require_permission
from app.errors import ApiError, NotFound
from app.logging import get_logger
from app.runs.schemas import RunOut
from app.schemas import ERROR_RESPONSES, ApiModel, Page, ProfileOut

log = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])
FINISHED = (RunStatus.completed, RunStatus.partial)


class AdminUserOut(ProfileOut):
    courses: int = 0
    runs: int = 0


class AdminUserCreate(ApiModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=256)
    full_name: str | None = Field(default=None, max_length=256)
    role: AppRole = AppRole.faculty
    must_change_password: bool = True


class AdminUserPatch(ApiModel):
    is_active: bool | None = None
    role: AppRole | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)
    must_change_password: bool | None = None


class AdminRunOut(RunOut):
    owner_email: str


class UsageRow(ApiModel):
    key: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    failures: int


class DemoResetOut(ApiModel):
    course_id: uuid.UUID
    deleted_runs: int


class DeptAttainmentRow(ApiModel):
    owner_email: str
    course_code: str
    run_id: uuid.UUID
    finished_at: datetime
    cos_met: int
    cos_total: int
    weakest_co: str | None


class DeptAuditRow(ApiModel):
    owner_email: str
    course_code: str
    run_id: uuid.UUID
    finished_at: datetime
    coverage_pct: float
    duplicates: int
    open_findings: int


def _profile_out(p: Profile) -> dict:
    from app.auth.router import profile_out

    return profile_out(p).model_dump()


@router.get("/users", response_model=Page[AdminUserOut], summary="All users (F-031)", responses=ERROR_RESPONSES,
            dependencies=[Depends(require_permission(Permission.admin_users))])
async def list_users(db: DbDep, page: Annotated[int, Query(ge=1)] = 1, page_size: Annotated[int, Query(ge=1, le=100)] = 25) -> Page[AdminUserOut]:
    total = (await db.execute(select(func.count()).select_from(Profile))).scalar_one()
    rows = list((await db.execute(select(Profile).order_by(Profile.created_at).offset((page - 1) * page_size).limit(page_size))).scalars())
    ids = [p.id for p in rows]
    course_counts: dict = {}
    run_counts: dict = {}
    if ids:
        course_counts = dict((await db.execute(
            select(Course.owner_id, func.count()).where(Course.owner_id.in_(ids), Course.deleted_at.is_(None)).group_by(Course.owner_id)
        )).all())
        run_counts = dict((await db.execute(
            select(Run.owner_id, func.count()).where(Run.owner_id.in_(ids)).group_by(Run.owner_id)
        )).all())
    items = [
        AdminUserOut(**_profile_out(p), courses=course_counts.get(p.id, 0), runs=run_counts.get(p.id, 0))
        for p in rows
    ]
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED, summary="Add user with email and password (F-031)", responses=ERROR_RESPONSES,
             dependencies=[Depends(require_permission(Permission.admin_users))])
async def create_user(data: AdminUserCreate, db: DbDep) -> AdminUserOut:
    email = data.email.strip().lower()
    existing = (await db.execute(select(Profile).where(Profile.email == email))).scalar_one_or_none()
    if existing is not None:
        raise ApiError("EMAIL_EXISTS", 409, f"A user with email '{email}' already exists")

    p = Profile(
        id=uuid.uuid4(),
        email=email,
        full_name=data.full_name.strip() if data.full_name else None,
        role=data.role,
        is_active=True,
        password_hash=hash_password(data.password),
        must_change_password=data.must_change_password,
    )
    db.add(p)
    await db.flush()
    log.info(
        "admin.user_created",
        user_id=str(p.id),
        email=p.email,
        role=p.role.value,
        must_change_password=p.must_change_password,
    )
    return AdminUserOut(**_profile_out(p), courses=0, runs=0)


@router.patch("/users/{user_id}", response_model=AdminUserOut, summary="Enable/disable a user or change role (F-031)", responses=ERROR_RESPONSES,
              dependencies=[Depends(require_permission(Permission.admin_users))])
async def patch_user(user_id: uuid.UUID, data: AdminUserPatch, db: DbDep, admin: UserDep) -> AdminUserOut:
    p = await db.get(Profile, user_id)
    if p is None:
        raise NotFound("USER_NOT_FOUND", "User not found")
    if p.id == admin.id and (data.is_active is False or (data.role is not None and data.role != AppRole.admin)):
        raise ApiError("VALIDATION_ERROR", 422, "You cannot disable or demote your own account")
    if data.is_active is not None:
        p.is_active = data.is_active
    if data.role is not None:
        p.role = data.role
    if data.password is not None:
        p.password_hash = hash_password(data.password)
    if data.must_change_password is not None:
        p.must_change_password = data.must_change_password
    await db.flush()
    log.info("admin.user_patched", user_id=str(p.id), is_active=p.is_active, role=p.role.value)
    courses = (await db.execute(select(func.count()).where(Course.owner_id == p.id, Course.deleted_at.is_(None)))).scalar_one()
    runs = (await db.execute(select(func.count()).where(Run.owner_id == p.id))).scalar_one()
    return AdminUserOut(**_profile_out(p), courses=courses, runs=runs)


@router.get("/runs", response_model=Page[AdminRunOut], summary="All runs across users (F-032)", responses=ERROR_RESPONSES,
            dependencies=[Depends(require_permission(Permission.admin_runs))])
async def list_runs(
    db: DbDep,
    module: Annotated[RunModule | None, Query()] = None,
    status_: Annotated[RunStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> Page[AdminRunOut]:
    stmt = select(Run, Profile.email).join(Profile, Profile.id == Run.owner_id)
    if module:
        stmt = stmt.where(Run.module == module)
    if status_:
        stmt = stmt.where(Run.status == status_)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(stmt.order_by(Run.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
    items = [AdminRunOut(**RunOut.model_validate(r).model_dump(), owner_email=email) for r, email in rows]
    return Page(items=items, page=page, page_size=page_size, total=total)


@router.get("/usage", response_model=list[UsageRow], summary="LLM usage/cost grouped by user or day (F-033)", responses=ERROR_RESPONSES,
            dependencies=[Depends(require_permission(Permission.admin_usage))])
async def usage(
    db: DbDep,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: Annotated[date | None, Query()] = None,
    group: Annotated[Literal["user", "day"], Query()] = "user",
) -> list[UsageRow]:
    start = datetime.combine(from_ or (date.today() - timedelta(days=30)), datetime.min.time(), tzinfo=UTC)
    end = datetime.combine((to or date.today()) + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    rows = list((await db.execute(select(UsageLog, Profile.email).outerjoin(Profile, Profile.id == UsageLog.user_id)
                                  .where(UsageLog.created_at >= start, UsageLog.created_at < end))).all())
    agg: dict[str, UsageRow] = {}
    for u, email in rows:
        key = (email or "system") if group == "user" else u.created_at.date().isoformat()
        r = agg.setdefault(key, UsageRow(key=key, calls=0, tokens_in=0, tokens_out=0, cost_usd=0.0, failures=0))
        r.calls += 1
        r.tokens_in += u.tokens_in or 0
        r.tokens_out += u.tokens_out or 0
        r.cost_usd = round(r.cost_usd + (u.cost_usd or 0.0), 6)
        r.failures += 1 if u.status == "failed" else 0
    return sorted(agg.values(), key=lambda r: r.key)


@router.post("/demo/reset", response_model=DemoResetOut, summary="Delete and re-seed the admin's demo course (F-034)", responses=ERROR_RESPONSES,
             dependencies=[Depends(require_permission(Permission.dashboard_admin))])
async def demo_reset(db: DbDep, admin: UserDep) -> DemoResetOut:
    demo_courses = list((await db.execute(select(Course).where(Course.is_demo.is_(True), Course.owner_id == admin.id))).scalars())
    deleted_runs = 0
    for c in demo_courses:
        deleted_runs += (await db.execute(select(func.count()).where(Run.course_id == c.id))).scalar_one()
        await db.execute(delete(Course).where(Course.id == c.id))  # FK cascades remove artefacts/runs/findings
    await db.flush()
    course, _ = await seed_demo(db, admin)
    log.info("admin.demo_reset", course_id=str(course.id), deleted_runs=deleted_runs)
    return DemoResetOut(course_id=course.id, deleted_runs=deleted_runs)


@router.get("/department/attainment", response_model=list[DeptAttainmentRow], summary="Latest attainment run per course, all faculty (F-035)",
            responses=ERROR_RESPONSES, dependencies=[Depends(require_permission(Permission.dashboard_admin_department))])
async def dept_attainment(db: DbDep) -> list[DeptAttainmentRow]:
    rows = (await db.execute(select(Run, Course.code, Profile.email).join(Course, Course.id == Run.course_id).join(Profile, Profile.id == Run.owner_id)
                             .where(Run.module == RunModule.attainment, Run.status.in_(FINISHED), Course.deleted_at.is_(None))
                             .order_by(Run.finished_at.desc()))).all()
    seen: set[uuid.UUID] = set()
    out = []
    for run, code, email in rows:
        if run.course_id in seen:
            continue
        seen.add(run.course_id)
        s = run.summary or {}
        cos = [c for c in s.get("cos", []) if c.get("students")]
        weakest = min(cos, key=lambda c: c["attained_pct"])["co_code"] if cos else None
        out.append(DeptAttainmentRow(owner_email=email, course_code=code, run_id=run.id, finished_at=run.finished_at,
                                     cos_met=int(s.get("cos_met", 0)), cos_total=int(s.get("cos_total", 0)), weakest_co=weakest))
    return out


@router.get("/department/exam-audits", response_model=list[DeptAuditRow], summary="Latest exam audit per course, all faculty (F-036)",
            responses=ERROR_RESPONSES, dependencies=[Depends(require_permission(Permission.dashboard_admin_department))])
async def dept_exam_audits(db: DbDep) -> list[DeptAuditRow]:
    rows = (await db.execute(select(Run, Course.code, Profile.email).join(Course, Course.id == Run.course_id).join(Profile, Profile.id == Run.owner_id)
                             .where(Run.module == RunModule.exam_audit, Run.status.in_(FINISHED), Course.deleted_at.is_(None))
                             .order_by(Run.finished_at.desc()))).all()
    seen: set[uuid.UUID] = set()
    latest: list[tuple] = []
    for run, code, email in rows:
        if run.course_id in seen:
            continue
        seen.add(run.course_id)
        latest.append((run, code, email))

    run_ids = [run.id for run, _, _ in latest]
    open_by_run: dict[uuid.UUID, int] = {}
    dups_by_run: dict[uuid.UUID, int] = {}
    if run_ids:
        open_by_run = dict((await db.execute(
            select(Finding.run_id, func.count()).where(Finding.run_id.in_(run_ids), Finding.status == FindingStatus.open).group_by(Finding.run_id)
        )).all())
        dups_by_run = dict((await db.execute(
            select(Finding.run_id, func.count()).where(Finding.run_id.in_(run_ids), Finding.type == FindingType.duplicate).group_by(Finding.run_id)
        )).all())

    out = []
    for run, code, email in latest:
        s = run.summary or {}
        out.append(DeptAuditRow(owner_email=email, course_code=code, run_id=run.id, finished_at=run.finished_at,
                                coverage_pct=float(s.get("coverage_pct", 0)), duplicates=dups_by_run.get(run.id, 0), open_findings=open_by_run.get(run.id, 0)))
    return out
