from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """All runtime configuration. Values come from the environment / backend/.env only."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: Literal["dev", "test", "prod"] = Field("dev", alias="ENV")
    database_url: str = Field(
        f"sqlite+aiosqlite:///{BACKEND_DIR / 'dev.db'}", alias="DATABASE_URL"
    )
    cors_origins: str = Field("http://localhost:5173", alias="CORS_ORIGINS")
    max_upload_mb: int = Field(10, alias="MAX_UPLOAD_MB", ge=1, le=50)
    storage_dir: Path = Field(BACKEND_DIR / "storage", alias="STORAGE_DIR")
    seed_data_dir: Path = Field(BACKEND_DIR.parent / "data" / "seed-data", alias="SEED_DATA_DIR")

    # auth
    auth_mode: Literal["dev", "local", "supabase"] = Field("dev", alias="AUTH_MODE")
    dev_user_email: str = Field("faculty.dev@example.edu", alias="DEV_USER_EMAIL")
    # AUTH_MODE=local: email+password sign-in, HS256 JWT signed with JWT_SECRET (no sign-up endpoint).
    jwt_secret: str | None = Field(None, alias="JWT_SECRET", min_length=32)
    jwt_ttl_s: int = Field(12 * 3600, alias="JWT_TTL_S", ge=300, le=7 * 24 * 3600)
    seed_faculty_email: str | None = Field(None, alias="SEED_FACULTY_EMAIL")
    seed_faculty_password: str | None = Field(None, alias="SEED_FACULTY_PASSWORD", min_length=8)
    seed_admin_email: str | None = Field(None, alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str | None = Field(None, alias="SEED_ADMIN_PASSWORD", min_length=8)
    supabase_url: str | None = Field(None, alias="SUPABASE_URL")
    supabase_publishable_key: str | None = Field(None, alias="SUPABASE_PUBLISHABLE_KEY")
    supabase_secret_key: str | None = Field(None, alias="SUPABASE_SECRET_KEY")
    supabase_jwks_url: str | None = Field(None, alias="SUPABASE_JWKS_URL")
    supabase_jwt_secret: str | None = Field(None, alias="SUPABASE_JWT_SECRET")

    # LLM
    llm_provider: Literal["mock", "openai_compatible", "openrouter"] = Field(
        "mock", alias="LLM_PROVIDER"
    )
    llm_base_url: str = Field("https://openrouter.ai/api/v1", alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(None, alias="LLM_API_KEY")
    llm_model: str = Field("openai/gpt-4o-mini", alias="LLM_MODEL")
    llm_fallback_models: str = Field("", alias="LLM_FALLBACK_MODELS")
    llm_timeout_s: float = Field(60.0, alias="LLM_TIMEOUT_S")
    llm_max_retries: int = Field(1, alias="LLM_MAX_RETRIES", ge=0, le=3)
    embed_base_url: str | None = Field(None, alias="EMBED_BASE_URL")
    embed_api_key: str | None = Field(None, alias="EMBED_API_KEY")
    embed_model: str = Field("openai/text-embedding-3-small", alias="EMBED_MODEL")

    rate_limit_enabled: bool = Field(True, alias="RATE_LIMIT_ENABLED")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @field_validator("cors_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("storage_dir", "seed_data_dir")
    @classmethod
    def _anchor_relative_paths(cls, v: Path) -> Path:
        # Relative paths in .env are relative to backend/, not to the process cwd.
        return v if v.is_absolute() else (BACKEND_DIR / v).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def fallback_model_list(self) -> list[str]:
        return [m.strip() for m in self.llm_fallback_models.split(",") if m.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
