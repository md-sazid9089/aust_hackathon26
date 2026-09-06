from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.auth.service import PERMISSION_DESCRIPTIONS, AuthService, dashboards_for, permissions_for
from app.db.enums import ROLE_PERMISSIONS, AppRole
from app.db.models import Profile
from app.deps import DbDep, SettingsDep, UserDep
from app.schemas import ERROR_RESPONSES, ApiModel, ProfileOut

router = APIRouter(tags=["auth"])


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=1, max_length=256)


class TokenOut(ApiModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    user: ProfileOut


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class RolePermissionsOut(ApiModel):
    role: AppRole
    dashboards: list[str]
    permissions: list[str]


class PermissionCatalogOut(ApiModel):
    permissions: dict[str, str]
    roles: list[RolePermissionsOut]


def profile_out(user: Profile) -> ProfileOut:
    return ProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        must_change_password=bool(getattr(user, "must_change_password", False)),
        created_at=user.created_at,
        permissions=permissions_for(user.role),
        dashboards=dashboards_for(user.role),
    )


@router.post(
    "/auth/login",
    response_model=TokenOut,
    summary="Sign in with email + password (AUTH_MODE=local)",
    description=(
        "Returns a short-lived HS256 JWT. Send it as `Authorization: Bearer <token>` (or `?access_token=` for SSE). "
        "There is no sign-up: accounts are provisioned by the operator (seed users / admin)."
    ),
    responses=ERROR_RESPONSES,
)
async def login(data: LoginIn, db: DbDep, settings: SettingsDep) -> TokenOut:
    user, token, exp = await AuthService(db, settings).login(data.email, data.password)
    return TokenOut(access_token=token, expires_at=exp, user=profile_out(user))


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out",
    description="Tokens are stateless; the client discards its token. Endpoint exists so the flow is explicit and audited.",
    responses=ERROR_RESPONSES,
)
async def logout(user: UserDep) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/auth/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password",
    responses=ERROR_RESPONSES,
)
async def change_password(data: ChangePasswordIn, db: DbDep, settings: SettingsDep, user: UserDep) -> Response:
    await AuthService(db, settings).change_password(user, data.current_password, data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=ProfileOut,
    summary="Current user profile",
    description="Profile of the authenticated user plus the dashboards and permissions its role grants.",
    responses=ERROR_RESPONSES,
)
async def me(user: UserDep) -> ProfileOut:
    return profile_out(user)


@router.get(
    "/auth/permissions",
    response_model=PermissionCatalogOut,
    summary="Role → dashboards/permissions matrix",
    description="Public catalog the frontend uses for route guards. Mirrors the `role_permissions` table.",
)
async def permission_catalog() -> PermissionCatalogOut:
    return PermissionCatalogOut(
        permissions={p.value: d for p, d in PERMISSION_DESCRIPTIONS.items()},
        roles=[
            RolePermissionsOut(role=role, dashboards=dashboards_for(role), permissions=permissions_for(role))
            for role in ROLE_PERMISSIONS
        ],
    )
