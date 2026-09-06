from __future__ import annotations

from typing import Any

import httpx

from app.ai.providers.base import AIProvider, ChatResult, EmbedResult, ProviderError


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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self.embed_base_url = (embed_base_url or base_url).rstrip("/")
        self.is_openrouter = is_openrouter or "openrouter.ai" in self.base_url
        if self.is_openrouter:
            self.name = "openrouter"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if self.is_openrouter:
            headers["HTTP-Referer"] = "https://github.com/md-sazid9089/aust_hackathon26"
            headers["X-Title"] = "Faculty Copilot"
        self._client = httpx.AsyncClient(headers=headers)
        self._embed_headers = {"Authorization": f"Bearer {embed_api_key or api_key}"}

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
        body: dict[str, Any] = {
            "model": model or self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            },
        }
        if self.is_openrouter:
            body["provider"] = {"require_parameters": True}
        data = await self._post(f"{self.base_url}/chat/completions", body, timeout_s)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if isinstance(content, list):  # some gateways return content parts
                content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed completion response", retryable=True) from exc
        usage = data.get("usage") or {}
        return ChatResult(
            content=content or "",
            model=data.get("model") or body["model"],
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            raw={"finish_reason": choice.get("finish_reason")},
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
            raise ProviderError("Malformed embeddings response", retryable=True) from exc
        if len(vectors) != len(texts):
            raise ProviderError("Embeddings count mismatch", retryable=True)
        usage = data.get("usage") or {}
        return EmbedResult(vectors=vectors, model=data.get("model") or self.embed_model, tokens_in=usage.get("prompt_tokens"))

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/models", timeout=5.0)
            return r.status_code < 500
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
            raise ProviderError("Model request timed out", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"Transport error: {type(exc).__name__}", retryable=True) from exc
        if r.status_code == 429 or r.status_code >= 500:
            raise ProviderError(f"Gateway returned {r.status_code}", retryable=True, status=r.status_code)
        if r.status_code >= 400:
            raise ProviderError(f"Gateway rejected request ({r.status_code})", retryable=False, status=r.status_code)
        try:
            return r.json()
        except ValueError as exc:
            raise ProviderError("Gateway returned non-JSON body", retryable=True) from exc
