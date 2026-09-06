from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import issue_local_jwt
from app.auth.passwords import hash_password, verify_password
from app.config import Settings
from app.db.enums import ROLE_PERMISSIONS, AppRole, Permission
from app.db.models import Profile, RolePermission, utcnow
from app.errors import ApiError, Forbidden, Unauthenticated
from app.logging import get_logger

log = get_logger(__name__)

PERMISSION_DESCRIPTIONS: dict[Permission, str] = {
    Permission.dashboard_courses: "Course list (/)",
    Permission.dashboard_course_workspace: "Course workspace: syllabus, outcomes, artefacts, history",
    Permission.dashboard_exam_audit: "P1 Exam Paper Auditor pages",
    Permission.dashboard_attainment: "P4 CO–PO Attainment pages",
    Permission.dashboard_syllabus_check: "P3 Syllabus Overlap/Gap pages",
    Permission.dashboard_calibration: "P2 Grading Calibration pages",
    Permission.dashboard_overview: "Cross-course dashboard (/dashboard)",
    Permission.dashboard_admin: "System admin panel (/admin)",
    Permission.dashboard_admin_department: "Department Head view (/admin/department)",
    Permission.courses_write: "Create, edit, delete own courses and outcomes",
    Permission.artefacts_write: "Upload / confirm artefacts",
    Permission.runs_start: "Start analysis runs",
    Permission.findings_decide: "Accept / dismiss / reopen findings",
    Permission.demo_seed: "Load the demo course into own workspace",
    Permission.admin_users: "List users, enable/disable accounts",
    Permission.admin_runs: "Browse all courses and runs (read-only)",
    Permission.admin_usage: "LLM usage / cost per user",
}


def permissions_for(role: AppRole) -> list[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS[role])


def dashboards_for(role: AppRole) -> list[str]:
    return sorted(p.value.split(":", 1)[1] for p in ROLE_PERMISSIONS[role] if p.value.startswith("dashboard:"))


async def sync_role_permissions(db: AsyncSession) -> None:
    """Make `role_permissions` match the code catalog (insert missing, drop stale)."""
    existing = {(r.role, r.permission): r for r in (await db.execute(select(RolePermission))).scalars()}
    wanted: set[tuple[AppRole, str]] = set()
    for role, perms in ROLE_PERMISSIONS.items():
        for p in perms:
            wanted.add((role, p.value))
            row = existing.get((role, p.value))
            desc = PERMISSION_DESCRIPTIONS.get(p)
            if row is None:
                db.add(RolePermission(role=role, permission=p.value, description=desc))
            elif row.description != desc:
                row.description = desc
    for key, row in existing.items():
        if key not in wanted:
            await db.delete(row)
    await db.flush()


async def ensure_seed_users(db: AsyncSession, settings: Settings) -> None:
    """Create/refresh the two sign-in accounts from env (local auth has no sign-up)."""
    for email, password, role, name in (
        (settings.seed_faculty_email, settings.seed_faculty_password, AppRole.faculty, "Demo Faculty"),
        (settings.seed_admin_email, settings.seed_admin_password, AppRole.admin, "Demo Admin"),
    ):
        if not (email and password):
            continue
        email = email.strip().lower()
        profile = (await db.execute(select(Profile).where(Profile.email == email))).scalar_one_or_none()
        if profile is None:
            profile = Profile(id=uuid.uuid4(), email=email, full_name=name, role=role)
            db.add(profile)
        profile.role = role
        profile.is_active = True
        if not verify_password(password, profile.password_hash):
            profile.password_hash = hash_password(password)
        log.info("auth.seed_user", email=email, role=role.value)
    await db.flush()


class AuthService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def login(self, email: str, password: str) -> tuple[Profile, str, int]:
        if self.settings.auth_mode != "local":
            raise ApiError("AUTH_MODE_UNSUPPORTED", 404, "Password sign-in is not enabled on this server")
        if not self.settings.jwt_secret:
            raise ApiError("AUTH_MISCONFIGURED", 503, "JWT_SECRET is not set")
        email = email.strip().lower()
        profile = (await self.db.execute(select(Profile).where(Profile.email == email))).scalar_one_or_none()
        # Same error for unknown email and wrong password (no account enumeration); verify runs either way.
        ok = verify_password(password, profile.password_hash if profile else None)
        if profile is None or not ok:
            raise Unauthenticated("Invalid email or password")
        if not profile.is_active:
            raise Forbidden("USER_INACTIVE", "This account is disabled")
        profile.last_login_at = utcnow()
        token, exp = issue_local_jwt(
            user_id=profile.id,
            email=profile.email,
            role=profile.role.value,
            secret=self.settings.jwt_secret,
            ttl_s=self.settings.jwt_ttl_s,
        )
        return profile, token, exp

    async def change_password(self, user: Profile, current: str, new: str) -> None:
        if not verify_password(current, user.password_hash):
            raise Unauthenticated("Current password is incorrect")
        user.password_hash = hash_password(new)
