from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class ProviderError(Exception):
    """Transport/HTTP failure talking to the model gateway."""

    def __init__(self, message: str, *, retryable: bool = True, status: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status


@dataclass
class ChatResult:
    content: str  # raw JSON text from the model
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    model: str
    tokens_in: int | None = None


class AIProvider(ABC):
    """Interface every LLM backend implements. Callers never see HTTP details."""

    name: str = "base"

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
        context: dict[str, Any] | None = None,
    ) -> ChatResult:
        """`context` is the structured payload the prompt was built from; real providers ignore it."""

    @abstractmethod
    async def embed(self, texts: list[str], *, timeout_s: float = 60.0) -> EmbedResult: ...

    async def health(self) -> bool:
        return True

    async def aclose(self) -> None:  # pragma: no cover
        return None
