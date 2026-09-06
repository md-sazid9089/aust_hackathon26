from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import verify_supabase_jwt
from app.config import Settings, get_settings
from app.db.enums import AppRole
from app.db.models import Profile
from app.db.session import get_sessionmaker
from app.errors import ApiError, Forbidden, Unauthenticated

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_db() -> AsyncIterator[AsyncSession]:
    """One transaction per request; commit on success, rollback on error."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbDep = Annotated[AsyncSession, Depends(get_db)]


async def _get_or_create_profile(
    db: AsyncSession, *, user_id: uuid.UUID | None, email: str, full_name: str | None = None
) -> Profile:
    stmt = select(Profile).where(Profile.id == user_id) if user_id else select(Profile).where(
        Profile.email == email
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if profile is None:
        profile = Profile(id=user_id or uuid.uuid4(), email=email, full_name=full_name)
        db.add(profile)
        await db.flush()
    return profile


def _bearer(request: Request, access_token: str | None) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return access_token  # SSE (EventSource cannot set headers)


async def get_current_user(
    request: Request,
    db: DbDep,
    settings: SettingsDep,
    access_token: Annotated[str | None, Query(include_in_schema=False)] = None,
    x_dev_user: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> Profile:
    if settings.auth_mode == "dev":
        # Local development: fixed faculty user; X-Dev-User overrides the email (tests, isolation checks).
        email = (x_dev_user or settings.dev_user_email).strip().lower()
        profile = await _get_or_create_profile(db, user_id=None, email=email, full_name="Dev Faculty")
    else:
        token = _bearer(request, access_token)
        if not token:
            raise Unauthenticated()
        if not settings.supabase_jwt_secret:
            raise ApiError("AUTH_MISCONFIGURED", 503, "Authentication is not configured")
        claims = verify_supabase_jwt(token, settings.supabase_jwt_secret)
        try:
            user_id = uuid.UUID(str(claims["sub"]))
        except ValueError as exc:
            raise Unauthenticated("Invalid subject") from exc
        email = str(claims.get("email") or f"{user_id}@unknown.local").lower()
        meta = claims.get("user_metadata") or {}
        profile = await _get_or_create_profile(
            db, user_id=user_id, email=email, full_name=meta.get("full_name")
        )
    if not profile.is_active:
        raise Forbidden("USER_INACTIVE", "This account is disabled")
    request.state.user_id = str(profile.id)
    return profile


UserDep = Annotated[Profile, Depends(get_current_user)]


def require_role(role: AppRole):
    async def _dep(user: UserDep) -> Profile:
        if user.role != role:
            raise Forbidden()
        return user

    return _dep


class RateLimiter:
    """In-memory sliding-window limiter keyed by user id (single-process MVP; swap for Redis later)."""

    def __init__(self, limit: int, window_s: int = 60) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, user: UserDep, settings: SettingsDep) -> None:
        if not settings.rate_limit_enabled:
            return
        now = time.monotonic()
        q = self._hits[str(user.id)]
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.limit:
            retry = int(self.window_s - (now - q[0])) + 1
            raise ApiError(
                "RATE_LIMITED",
                429,
                "Too many requests",
                {"retry_after_s": retry},
                headers={"Retry-After": str(retry)},
            )
        q.append(now)


runs_rate_limit = RateLimiter(limit=10)
uploads_rate_limit = RateLimiter(limit=20)
