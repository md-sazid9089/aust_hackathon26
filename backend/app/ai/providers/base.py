from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

ErrorKind = Literal[
    "timeout",      # client-side timeout → try the next model immediately
    "rate_limit",   # 429 → next model (same-model retry would just burn budget)
    "server",       # 5xx / non-JSON body → next model
    "transport",    # connection reset, DNS… → next model
    "malformed",    # 200 but the response shape is wrong → next model
    "truncated",    # finish_reason=length → caller shrinks the request; never retried as-is
    "refusal",      # model refused → final, no retry anywhere
    "auth",         # 401/403 → final, every model shares the key
    "bad_request",  # other 4xx → final for this model (schema/param unsupported)
]


class ProviderError(Exception):
    """Transport/HTTP/model failure talking to the gateway. `kind` drives the retry policy."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = True,
        status: int | None = None,
        kind: ErrorKind = "transport",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status
        self.kind = kind
        self.retry_after = retry_after  # seconds, from the gateway's Retry-After header when present

    @property
    def final(self) -> bool:
        """No model in the fallback chain can fix this."""
        return self.kind in ("refusal", "auth")


@dataclass
class ChatResult:
    content: str  # raw JSON text from the model
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    finish_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def truncated(self) -> bool:
        return self.finish_reason == "length"


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    model: str
    tokens_in: int | None = None


class AIProvider(ABC):
    """Interface every LLM backend implements. Callers never see HTTP details."""

    name: str = "base"
    embed_model_name: str = "base-embed"  # canonical id stored next to vectors; a change forces re-embedding
    # Response mode the gateway is known to accept ("json_schema" | "json_object" | "prompt"); learned by the client.
    response_mode: str | None = None

    @abstractmethod
    async def chat_json(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        schema_name: str,
        model: str | None = None,
        temperature: float = 0.0,
        timeout_s: float = 60.0,
        max_completion_tokens: int | None = None,
        context: dict[str, Any] | None = None,
        seed: int | None = None,
        response_mode: str = "json_schema",
        repair: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        """`context` is the structured payload the prompt was built from; real providers ignore it.

        `repair` is an optional [assistant, user] message pair appended after the user turn so the
        model can correct JSON that failed validation.
        """

    @abstractmethod
    async def embed(self, texts: list[str], *, timeout_s: float = 60.0) -> EmbedResult: ...

    async def health(self) -> bool:
        return True

    async def aclose(self) -> None:  # pragma: no cover
        return None
