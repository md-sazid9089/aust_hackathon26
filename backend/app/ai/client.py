from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import AIProvider, ProviderError
from app.ai.providers.mock import MockProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.config import Settings, get_settings
from app.db.enums import UsagePurpose
from app.db.models import UsageLog
from app.logging import get_logger

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

_provider: AIProvider | None = None


def build_provider(settings: Settings) -> AIProvider:
    if settings.llm_provider == "mock":
        return MockProvider()
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is required unless LLM_PROVIDER=mock")
    return OpenAICompatibleProvider(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        embed_model=settings.embed_model,
        embed_base_url=settings.embed_base_url,
        embed_api_key=settings.embed_api_key,
        is_openrouter=settings.llm_provider == "openrouter",
    )


def get_provider() -> AIProvider:
    global _provider
    if _provider is None:
        _provider = build_provider(get_settings())
    return _provider


def set_provider(provider: AIProvider | None) -> None:
    """Override the process-wide provider (tests / startup)."""
    global _provider
    _provider = provider


@dataclass
class CallContext:
    user_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None


@dataclass
class StructuredResult:
    value: BaseModel | None
    model: str | None
    attempts: int
    error: str | None = None


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def _recover_json(text: str) -> Any:
    """Parse model output; tolerate code fences / leading prose around a single JSON object."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK.search(text)
        if not m:
            raise
        return json.loads(m.group(0))


async def _log_usage(
    db: AsyncSession | None,
    *,
    ctx: CallContext,
    purpose: UsagePurpose,
    model: str,
    tokens_in: int | None,
    tokens_out: int | None,
    latency_ms: int,
    status: str,
) -> None:
    if db is None:
        return
    db.add(
        UsageLog(
            user_id=ctx.user_id, run_id=ctx.run_id, purpose=purpose, model=model,
            tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms, status=status,
        )
    )


async def structured_call(
    *,
    purpose: str,
    usage_purpose: UsagePurpose,
    system: str,
    user: str,
    schema: type[T],
    ctx: CallContext,
    db: AsyncSession | None = None,
    context: dict[str, Any] | None = None,
    provider: AIProvider | None = None,
) -> StructuredResult:
    """Call the model, validate against `schema`; retry once on invalid output / retryable errors.

    Never raises for model problems: returns `value=None` with `error` so callers can degrade to `partial`.
    """
    settings = get_settings()
    provider = provider or get_provider()
    models = [None, *settings.fallback_model_list] if provider.name != "mock" else [None]
    max_attempts = 1 + settings.llm_max_retries
    json_schema = schema.model_json_schema()
    _strictify(json_schema)
    last_error: str | None = None
    attempt = 0
    for model in models:
        for _ in range(max_attempts):
            attempt += 1
            started = time.perf_counter()
            used_model = model or getattr(provider, "model", provider.name)
            try:
                result = await provider.chat_json(
                    purpose=purpose, system=system, user=user, json_schema=json_schema,
                    schema_name=schema.__name__, model=model, temperature=0.0,
                    timeout_s=settings.llm_timeout_s, context=context,
                )
                used_model = result.model
                value = schema.model_validate(_recover_json(result.content))
                await _log_usage(
                    db, ctx=ctx, purpose=usage_purpose, model=used_model, tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out, latency_ms=int((time.perf_counter() - started) * 1000),
                    status="ok" if attempt == 1 else "retry",
                )
                return StructuredResult(value=value, model=used_model, attempts=attempt)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = f"invalid_output: {type(exc).__name__}"
                log.warning("llm.invalid_output", purpose=purpose, attempt=attempt, error=type(exc).__name__)
            except ProviderError as exc:
                last_error = f"provider_error: {exc}"
                log.warning("llm.provider_error", purpose=purpose, attempt=attempt, error=str(exc))
                if not exc.retryable:
                    break
            await _log_usage(
                db, ctx=ctx, purpose=usage_purpose, model=str(used_model), tokens_in=None, tokens_out=None,
                latency_ms=int((time.perf_counter() - started) * 1000), status="failed",
            )
    return StructuredResult(value=None, model=None, attempts=attempt, error=last_error)


def _strictify(schema: dict[str, Any]) -> None:
    """OpenAI strict mode requires additionalProperties=false and all properties required."""
    if schema.get("type") == "object" and "properties" in schema:
        schema["additionalProperties"] = False
        schema["required"] = list(schema["properties"].keys())
    for key in ("properties", "$defs"):
        for sub in schema.get(key, {}).values():
            if isinstance(sub, dict):
                _strictify(sub)
    for key in ("items", "anyOf", "allOf"):
        sub = schema.get(key)
        if isinstance(sub, dict):
            _strictify(sub)
        elif isinstance(sub, list):
            for s in sub:
                if isinstance(s, dict):
                    _strictify(s)
