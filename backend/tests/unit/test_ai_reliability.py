"""Reliability policy of `structured_call`: response-mode ladder, repair turn, backoff, strict schema, JSON recovery."""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import BaseModel, ConfigDict, Field

from app.ai import client as C
from app.ai.client import CallContext, _recover_json, _strictify, structured_call
from app.ai.embeddings import embed_texts
from app.ai.providers.base import ProviderError
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.db.enums import UsagePurpose
from app.modules.exam_audit.graph import quote_is_verbatim


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[str] = Field(max_length=5)
    score: float = Field(ge=0, le=1, default=0.5)
    rationale: str


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def fake_sleep(_s):
        return None

    monkeypatch.setattr(C.asyncio, "sleep", fake_sleep)


# --- JSON recovery -----------------------------------------------------------
@pytest.mark.parametrize(
    "raw",
    [
        'Here you go:\n```json\n{"items": ["a"], "rationale": "ok"}\n```\nHope this helps!',
        '{"items": ["a",], "rationale": "ok",}',  # trailing commas
        '{“items”: [“a”], “rationale”: “ok”}',  # smart quotes
        'First a sketch {"draft": 1} and the real one: {"items": ["a"], "rationale": "ok"} done.',
        '```\n{"items": ["a"], "rationale": "ok"}\n```',
    ],
)
def test_recover_json_relaxed_outputs(raw):
    assert _recover_json(raw, expected_keys={"items", "rationale"}) == {"items": ["a"], "rationale": "ok"}


def test_recover_json_raises_when_nothing_parses():
    with pytest.raises(json.JSONDecodeError):
        _recover_json("no json here at all")


# --- strict schema -----------------------------------------------------------
def test_strictify_strips_unsupported_keywords_and_defaults():
    schema = Out.model_json_schema()
    assert "default" in schema["properties"]["score"] and "maxItems" in schema["properties"]["items"]
    _strictify(schema)
    assert "default" not in schema["properties"]["score"]
    assert not {"minimum", "maximum"} & schema["properties"]["score"].keys()
    assert "maxItems" not in schema["properties"]["items"]
    assert set(schema["required"]) == {"items", "score", "rationale"} and schema["additionalProperties"] is False


# --- repair turn --------------------------------------------------------------
async def test_invalid_output_triggers_repair_turn_with_previous_output(mock_provider):
    mock_provider.queue("p", '{"items": "oops", "rationale": "r"}')
    mock_provider.queue("p", '{"items": ["fixed"], "score": 0.1, "rationale": "r"}')
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value is not None and res.value.items == ["fixed"] and res.repaired and res.attempts == 2
    assert mock_provider.calls[0]["repair"] is False and mock_provider.calls[1]["repair"] is True


# --- response-mode ladder -----------------------------------------------------
@pytest.fixture
def provider():
    return OpenAICompatibleProvider(base_url="https://llm.test/v1", api_key="k", model="m", embed_model="e")


@respx.mock
async def test_response_format_ladder_downgrades_and_is_remembered(provider, monkeypatch):
    monkeypatch.setattr(C, "get_provider", lambda: provider)
    route = respx.post("https://llm.test/v1/chat/completions")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if "response_format" in body:
            return httpx.Response(400, json={"error": {"type": "no_providers"}})
        assert "JSON Schema" in body["messages"][0]["content"]  # prompt mode carries the schema
        return httpx.Response(200, json={"model": "llm7/default", "choices": [{"message": {"content": 'Sure!\n```json\n{"items": ["a"], "score": 0.2, "rationale": "ok"}\n```'}, "finish_reason": "stop"}]})

    route.mock(side_effect=handler)
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext(), provider=provider)
    assert res.value is not None and res.response_mode == "prompt" and res.attempts == 1
    assert route.call_count == 3  # json_schema → json_object → prompt
    assert provider.response_mode == "prompt"
    # second call starts directly in the remembered mode
    res2 = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext(), provider=provider)
    assert res2.value is not None and route.call_count == 4


@respx.mock
async def test_provider_sends_seed_max_tokens_and_repair_messages(provider):
    respx.post("https://llm.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"model": "m", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]})
    )
    await provider.chat_json(
        purpose="p", system="s", user="u", json_schema={}, schema_name="X", max_completion_tokens=321, seed=7,
        response_mode="json_object", repair=[{"role": "assistant", "content": "bad"}, {"role": "user", "content": "fix"}],
    )
    sent = json.loads(respx.calls.last.request.content)
    assert sent["max_tokens"] == 321 and sent["seed"] == 7 and sent["response_format"] == {"type": "json_object"}
    assert [m["role"] for m in sent["messages"]] == ["system", "user", "assistant", "user"]


@respx.mock
async def test_retry_after_header_and_truncation_are_surfaced(provider):
    route = respx.post("https://llm.test/v1/chat/completions")
    route.mock(return_value=httpx.Response(429, headers={"Retry-After": "3"}))
    with pytest.raises(ProviderError) as e:
        await provider.chat_json(purpose="p", system="s", user="u", json_schema={}, schema_name="X")
    assert e.value.kind == "rate_limit" and e.value.retry_after == 3.0
    route.mock(return_value=httpx.Response(200, json={"model": "m", "choices": [{"message": {"content": '{"items": ['}, "finish_reason": "length"}]}))
    res = await provider.chat_json(purpose="p", system="s", user="u", json_schema={}, schema_name="X")
    assert res.truncated


async def test_final_errors_stop_fallback_chain(mock_provider):
    mock_provider.queue("p", ProviderError("refused", retryable=False, kind="refusal"))
    mock_provider.queue("p", '{"items": [], "score": 0, "rationale": "never"}')
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value is None and res.attempts == 1 and "refused" in res.error


async def test_prompt_hash_is_stable_and_prompt_sensitive(mock_provider):
    mock_provider.queue("p", '{"items": [], "score": 0, "rationale": "a"}')
    mock_provider.queue("p", '{"items": [], "score": 0, "rationale": "b"}')
    r1 = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    r2 = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s2", user="u", schema=Out, ctx=CallContext())
    assert r1.prompt_hash and r1.prompt_hash != r2.prompt_hash


# --- embeddings ---------------------------------------------------------------
class _DimFlipProvider:
    name = "flip"
    embed_model_name = "flip-embed"

    async def embed(self, texts, *, timeout_s=60.0):
        from app.ai.providers.base import EmbedResult

        return EmbedResult(vectors=[[1.0, 0.0] if i % 2 == 0 else [1.0, 0.0, 0.0] for i in range(len(texts))], model="whatever/alias")


async def test_embed_texts_rejects_mixed_dimensions_and_reports_canonical_model():
    assert await embed_texts(["a", "b"], ctx=CallContext(), provider=_DimFlipProvider()) is None  # type: ignore[arg-type]


async def test_embed_texts_normalises_and_uses_configured_model_name(mock_provider):
    res = await embed_texts(["hello world"], ctx=CallContext(), provider=mock_provider)
    assert res is not None
    vectors, model = res
    assert model == mock_provider.embed_model_name
    assert abs(sum(v * v for v in vectors[0]) - 1.0) < 1e-6


# --- evidence verification ------------------------------------------------------
def test_quote_is_verbatim_is_whitespace_and_case_insensitive():
    src = "Write an SQL   query to list\nthe employees whose salary exceeds the average."
    assert quote_is_verbatim("write an sql query", src)
    assert quote_is_verbatim("list the employees", src)
    assert not quote_is_verbatim("compose a query", src)
    assert not quote_is_verbatim("SQL", src)  # too short to be evidence
