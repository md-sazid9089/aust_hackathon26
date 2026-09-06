from fastapi import APIRouter

from app.deps import UserDep
from app.schemas import ERROR_RESPONSES, ProfileOut

router = APIRouter(tags=["auth"])


@router.get(
    "/me",
    response_model=ProfileOut,
    summary="Current user profile",
    description="Returns the profile of the authenticated faculty/admin user.",
    responses=ERROR_RESPONSES,
)
async def me(user: UserDep) -> ProfileOut:
    return ProfileOut.model_validate(user)
