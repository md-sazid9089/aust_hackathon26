from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import httpx

from app.ai.providers.base import AIProvider, ChatResult, EmbedResult, ProviderError

# Models that accept `reasoning_effort` on chat completions (OpenAI direct). Older gpt-4* reject it.
_REASONING_MODEL_RE = re.compile(r"(^|/)(gpt-5|o[1-9])", re.IGNORECASE)


def is_reasoning_model(model: str) -> bool:
    return bool(_REASONING_MODEL_RE.search(model))


class OpenAICompatibleProvider(AIProvider):
    """Any OpenAI-compatible chat/embeddings gateway (OpenAI, OpenRouter, local proxies)."""

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        embed_model: str,
        embed_base_url: str | None = None,
        embed_api_key: str | None = None,
        is_openrouter: bool = False,
        reasoning_effort: str | None = "none",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self.embed_model_name = embed_model
        self.embed_base_url = (embed_base_url or base_url).rstrip("/")
        host = (urlparse(self.base_url).hostname or "").lower()
        self.is_openrouter = is_openrouter or host == "openrouter.ai" or host.endswith(".openrouter.ai")
        self.is_openai = host == "api.openai.com"
        self.reasoning_effort = reasoning_effort or None
        if self.is_openrouter:
            self.name = "openrouter"
        elif self.is_openai:
            self.name = "openai"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if self.is_openrouter:
            headers["HTTP-Referer"] = "https://github.com/md-sazid9089/aust_hackathon26"
            headers["X-Title"] = "Faculty Copilot"
        self._client = httpx.AsyncClient(headers=headers)
        self._embed_headers = {"Authorization": f"Bearer {embed_api_key or api_key}"}

    def build_chat_body(
        self,
        *,
        model: str | None,
        system: str,
        user: str,
        json_schema: dict[str, Any],
        schema_name: str,
        temperature: float,
        max_completion_tokens: int | None,
    ) -> dict[str, Any]:
        model_id = model or self.model
        body: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            },
        }
        if max_completion_tokens:
            body["max_completion_tokens"] = int(max_completion_tokens)
        reasoning = is_reasoning_model(model_id)
        if reasoning and self.reasoning_effort:
            if self.is_openrouter:
                body["reasoning"] = {"effort": self.reasoning_effort}
            else:
                body["reasoning_effort"] = self.reasoning_effort
        # Reasoning models reject `temperature` unless reasoning is off.
        if not reasoning or self.reasoning_effort == "none":
            body["temperature"] = temperature
        if self.is_openrouter:
            body["provider"] = {"require_parameters": True, "data_collection": "deny"}
        return body

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
    ) -> ChatResult:
        body = self.build_chat_body(
            model=model, system=system, user=user, json_schema=json_schema, schema_name=schema_name,
            temperature=temperature, max_completion_tokens=max_completion_tokens,
        )
        data = await self._post(f"{self.base_url}/chat/completions", body, timeout_s)
        try:
            choice = data["choices"][0]
            message = choice["message"]
            content = message.get("content")
            if isinstance(content, list):  # some gateways return content parts
                content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ProviderError("Malformed completion response", retryable=True, kind="malformed") from exc
        finish_reason = choice.get("finish_reason")
        if message.get("refusal"):
            raise ProviderError("Model refused the request", retryable=False, kind="refusal")
        if finish_reason == "length":
            raise ProviderError("Output truncated (max_completion_tokens)", retryable=False, kind="truncated")
        if finish_reason == "content_filter":
            raise ProviderError("Output blocked by content filter", retryable=False, kind="refusal")
        usage = data.get("usage") or {}
        return ChatResult(
            content=content or "",
            model=data.get("model") or body["model"],
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            finish_reason=finish_reason,
            raw={"finish_reason": finish_reason},
        )

    async def embed(self, texts: list[str], *, timeout_s: float = 60.0) -> EmbedResult:
        body = {"model": self.embed_model, "input": texts}
        data = await self._post(
            f"{self.embed_base_url}/embeddings", body, timeout_s, headers=self._embed_headers
        )
        try:
            items = sorted(data["data"], key=lambda d: d.get("index", 0))
            vectors = [list(map(float, d["embedding"])) for d in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError("Malformed embeddings response", retryable=True, kind="malformed") from exc
        if len(vectors) != len(texts):
            raise ProviderError("Embeddings count mismatch", retryable=True, kind="malformed")
        usage = data.get("usage") or {}
        return EmbedResult(vectors=vectors, model=data.get("model") or self.embed_model, tokens_in=usage.get("prompt_tokens"))

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/models", timeout=5.0)
            return r.status_code < 400
        except httpx.HTTPError:
            return False

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post(
        self, url: str, body: dict[str, Any], timeout_s: float, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        try:
            r = await self._client.post(url, json=body, timeout=timeout_s, headers=headers)
        except httpx.TimeoutException as exc:
            raise ProviderError("Model request timed out", retryable=True, kind="timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Transport error: {type(exc).__name__}", retryable=True, kind="transport") from exc
        if r.status_code == 429:
            raise ProviderError("Gateway rate-limited the request (429)", retryable=True, status=429, kind="rate_limit")
        if r.status_code >= 500:
            raise ProviderError(f"Gateway returned {r.status_code}", retryable=True, status=r.status_code, kind="server")
        if r.status_code in (401, 403):
            raise ProviderError(f"Gateway rejected credentials ({r.status_code})", retryable=False, status=r.status_code, kind="auth")
        if r.status_code >= 400:
            raise ProviderError(f"Gateway rejected request ({r.status_code})", retryable=False, status=r.status_code, kind="bad_request")
        try:
            return r.json()
        except ValueError as exc:
            raise ProviderError("Gateway returned non-JSON body", retryable=True, kind="server") from exc
