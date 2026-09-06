from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="after")
    def _utc_timestamps(self):
        # SQLite returns naive datetimes; the API contract is ISO-8601 UTC.
        for name in type(self).model_fields:
            v = getattr(self, name, None)
            if isinstance(v, datetime) and v.tzinfo is None:
                object.__setattr__(self, name, v.replace(tzinfo=UTC))
        return self


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class ProfileOut(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    must_change_password: bool = False
    created_at: datetime
    permissions: list[str] = Field(default_factory=list)
    dashboards: list[str] = Field(default_factory=list)


ERROR_RESPONSES = {
    401: {"model": ErrorEnvelope, "description": "UNAUTHENTICATED"},
    403: {"model": ErrorEnvelope, "description": "FORBIDDEN / USER_INACTIVE"},
    404: {"model": ErrorEnvelope, "description": "*_NOT_FOUND"},
    409: {"model": ErrorEnvelope, "description": "Conflict"},
    422: {"model": ErrorEnvelope, "description": "VALIDATION_ERROR"},
    429: {"model": ErrorEnvelope, "description": "RATE_LIMITED"},
}
