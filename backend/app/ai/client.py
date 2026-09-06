from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.budget import CircuitBreaker, RunDeadline
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
breaker = CircuitBreaker()
# Bounds concurrent model calls across background tasks so one upload burst cannot exhaust the gateway.
_llm_gate: asyncio.Semaphore | None = None
_LLM_MAX_CONCURRENCY = 4

# Strict json_schema (OpenAI) is the production target; the ladder degrades for gateways that reject
# `response_format` (local free proxies return 400 for any value).
ResponseMode = Literal["json_schema", "json_object", "prompt"]
_RESPONSE_MODE_LADDER: tuple[ResponseMode, ...] = ("json_schema", "json_object", "prompt")


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
    breaker.reset()


def _gate() -> asyncio.Semaphore:
    global _llm_gate
    if _llm_gate is None:
        _llm_gate = asyncio.Semaphore(_LLM_MAX_CONCURRENCY)
    return _llm_gate


@dataclass
class CallContext:
    user_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    deadline: RunDeadline | None = None


@dataclass
class StructuredResult:
    value: BaseModel | None
    model: str | None
    attempts: int
    error: str | None = None
    prompt_hash: str | None = None
    response_mode: ResponseMode | None = None
    repaired: bool = False
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# JSON recovery. Relaxed gateways wrap JSON in prose or fences, use smart quotes, leave trailing
# commas, or emit several blocks; we pick the one that parses and carries our top-level keys.
_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)
_SMART_QUOTES = {"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'"}
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")


def _candidates(text: str) -> list[str]:
    text = text.strip()
    out: list[str] = [text] if text else []
    out.extend(m.group(1).strip() for m in _FENCE_RE.finditer(text))
    for opener, closer in (("{", "}"), ("[", "]")):
        depth, start, in_str, esc = 0, -1, False, False
        for i, ch in enumerate(text):
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                if depth == 0:
                    start = i
                depth += 1
            elif ch == closer and depth:
                depth -= 1
                if depth == 0 and start >= 0:
                    out.append(text[start : i + 1])
    return out


def _loads_lenient(s: str) -> Any:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        fixed = "".join(_SMART_QUOTES.get(c, c) for c in s)
        fixed = _TRAILING_COMMA_RE.sub(r"\1", fixed)
        return json.loads(fixed)


def _recover_json(text: str, *, expected_keys: set[str] | None = None) -> Any:
    """Parse model output tolerating fences, prose, smart quotes, trailing commas and multiple blocks."""
    last_exc: json.JSONDecodeError | None = None
    fallback: Any = None
    for cand in _candidates(text):
        try:
            obj = _loads_lenient(cand)
        except json.JSONDecodeError as exc:
            last_exc = exc
            continue
        if isinstance(obj, dict) and (not expected_keys or expected_keys & obj.keys()):
            return obj
        if fallback is None:
            fallback = obj
    if fallback is not None:
        return fallback
    raise last_exc or json.JSONDecodeError("no JSON found", text, 0)


# ---------------------------------------------------------------------------
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


def prompt_hash(system: str, user: str) -> str:
    """Stable id of the exact prompt sent, for provenance (the templated payload alone is not enough)."""
    return hashlib.sha256((system + "\n\x1e\n" + user).encode()).hexdigest()[:16]


def _schema_prompt_suffix(json_schema: dict[str, Any], schema_name: str) -> str:
    return (
        f"\n\nOutput format: respond with ONE JSON object ({schema_name}) that validates against this JSON Schema. "
        "No prose, no code fences, no extra keys.\n" + json.dumps(json_schema, ensure_ascii=False)
    )


def _estimate_max_tokens(user: str) -> int:
    # Output is at most a structured restatement of the input (≈4 chars/token); bounded for cost.
    return int(min(8000, max(1200, len(user) // 2)))


def _validation_summary(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', ())) or '$'}: {e.get('msg')}" for e in exc.errors()[:8]
        )
    return f"{type(exc).__name__}: {str(exc)[:200]}"


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
    """Call the model and validate against `schema`.

    Policy: strict json_schema first, stepping down the response-mode ladder when the gateway rejects
    the request shape; invalid output gets a repair turn carrying the validator's errors; retryable
    transport errors back off with jitter (honouring Retry-After); non-retryable errors move to the
    next fallback model; refusal/auth stop everything. Never raises for model problems — returns
    `value=None` with `error` so callers degrade to `partial`.
    """
    settings = get_settings()
    provider = provider or get_provider()
    is_mock = provider.name == "mock"
    models: list[str | None] = [None, *settings.fallback_model_list] if not is_mock else [None]
    max_attempts = 1 + settings.llm_max_retries
    json_schema = schema.model_json_schema()
    _strictify(json_schema)
    expected_keys = set(json_schema.get("properties", {}).keys())
    p_hash = prompt_hash(system, user)
    max_tokens = _estimate_max_tokens(user)
    mode: ResponseMode = _preferred_mode(provider)

    last_error: str | None = None
    attempt = 0
    repaired = False
    warnings: list[str] = []

    def done(value: BaseModel | None, model: str | None) -> StructuredResult:
        return StructuredResult(value, model, attempt, None if value else last_error, p_hash, mode, repaired, warnings)

    for model in models:
        model_key = model or getattr(provider, "model", provider.name)
        if breaker.is_open(model_key):
            warnings.append(f"model {model_key} skipped: circuit open")
            continue
        repair: list[dict[str, str]] | None = None
        tries = 0
        while tries < max_attempts:
            if ctx.deadline is not None and ctx.deadline.call_timeout() <= 0:
                last_error = "deadline: run time budget exhausted"
                return done(None, None)
            tries += 1
            attempt += 1
            started = time.perf_counter()
            used_model = model_key
            timeout_s = settings.llm_timeout_s if ctx.deadline is None else ctx.deadline.call_timeout(settings.llm_timeout_s)
            eff_system = system if mode != "prompt" else system + _schema_prompt_suffix(json_schema, schema.__name__)
            raw_content = ""
            try:
                async with _gate():
                    result = await provider.chat_json(
                        purpose=purpose, system=eff_system, user=user, json_schema=json_schema,
                        schema_name=schema.__name__, model=model, temperature=0.0, timeout_s=timeout_s,
                        context=context, max_completion_tokens=max_tokens, seed=settings.llm_seed,
                        response_mode=mode, repair=repair,
                    )
                used_model = result.model or model_key
                raw_content = result.content or ""
                value = schema.model_validate(_recover_json(raw_content, expected_keys=expected_keys))
                breaker.record_success(model_key)
                _remember_mode(provider, mode)
                await _log_usage(
                    db, ctx=ctx, purpose=usage_purpose, model=used_model, tokens_in=result.tokens_in,
                    tokens_out=result.tokens_out, latency_ms=int((time.perf_counter() - started) * 1000),
                    status="ok" if attempt == 1 else "retry",
                )
                return done(value, used_model)
            except (ValidationError, json.JSONDecodeError, ValueError) as exc:
                last_error = f"invalid_output: {type(exc).__name__}"
                log.warning("llm.invalid_output", purpose=purpose, attempt=attempt, mode=mode, error=type(exc).__name__)
                repair = [
                    {"role": "assistant", "content": raw_content[:6000] or "(empty)"},
                    {"role": "user", "content": f"That JSON failed validation: {_validation_summary(exc)}. Return the corrected JSON object only."},
                ]
                repaired = True
            except ProviderError as exc:
                last_error = f"provider_error: {exc}"
                log.warning("llm.provider_error", purpose=purpose, attempt=attempt, mode=mode, kind=exc.kind, error=str(exc))
                if exc.kind == "bad_request" and mode != "prompt":
                    # Request shape rejected (almost always response_format): step down without spending a retry.
                    mode = _next_mode(mode)
                    warnings.append(f"response_format downgraded to {mode}")
                    tries -= 1
                    attempt -= 1
                    continue
                if exc.kind == "truncated" and max_tokens < 8000:
                    max_tokens = 8000
                    continue
                if exc.final:
                    await _log_usage(db, ctx=ctx, purpose=usage_purpose, model=str(used_model), tokens_in=None, tokens_out=None, latency_ms=int((time.perf_counter() - started) * 1000), status="failed")
                    return done(None, None)
                breaker.record_failure(model_key)
                if not exc.retryable or (ctx.deadline is not None and not ctx.deadline.may_retry()):
                    await _log_usage(db, ctx=ctx, purpose=usage_purpose, model=str(used_model), tokens_in=None, tokens_out=None, latency_ms=int((time.perf_counter() - started) * 1000), status="failed")
                    break
                if tries < max_attempts:
                    await asyncio.sleep(_backoff(tries, retry_after=exc.retry_after))
            await _log_usage(
                db, ctx=ctx, purpose=usage_purpose, model=str(used_model), tokens_in=None, tokens_out=None,
                latency_ms=int((time.perf_counter() - started) * 1000), status="failed",
            )
    return done(None, None)


def _backoff(tries: int, *, retry_after: float | None) -> float:
    if retry_after:
        return min(float(retry_after), 20.0)
    return min(0.5 * (2 ** (tries - 1)), 6.0) + random.uniform(0.0, 0.3)


# Per-provider memory of the response mode the gateway accepts, so we do not pay a 400 on every call.
def _preferred_mode(provider: AIProvider) -> ResponseMode:
    return getattr(provider, "response_mode", None) or "json_schema"


def _remember_mode(provider: AIProvider, mode: ResponseMode) -> None:
    if hasattr(provider, "response_mode"):
        provider.response_mode = mode


def _next_mode(mode: ResponseMode) -> ResponseMode:
    i = _RESPONSE_MODE_LADDER.index(mode)
    return _RESPONSE_MODE_LADDER[min(i + 1, len(_RESPONSE_MODE_LADDER) - 1)]


# OpenAI strict mode: every property required, additionalProperties=false, and none of these keywords.
_STRICT_UNSUPPORTED = (
    "default", "format", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern", "minItems", "maxItems", "uniqueItems",
)


def _strictify(schema: dict[str, Any]) -> None:
    """Make a Pydantic JSON schema acceptable to OpenAI strict mode (Pydantic still enforces the bounds)."""
    for k in _STRICT_UNSUPPORTED:
        schema.pop(k, None)
    if schema.get("type") == "object" and "properties" in schema:
        schema["additionalProperties"] = False
        schema["required"] = list(schema["properties"].keys())
    for key in ("properties", "$defs"):
        for sub in schema.get(key, {}).values():
            if isinstance(sub, dict):
                _strictify(sub)
    for key in ("items", "anyOf", "allOf", "oneOf"):
        sub = schema.get(key)
        if isinstance(sub, dict):
            _strictify(sub)
        elif isinstance(sub, list):
            for s in sub:
                if isinstance(s, dict):
                    _strictify(s)
