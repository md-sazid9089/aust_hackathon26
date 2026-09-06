from __future__ import annotations

import json

import httpx
import pytest
import respx
from pydantic import BaseModel, ConfigDict

from app.ai.client import CallContext, _strictify, structured_call
from app.ai.providers.base import ProviderError
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.db.enums import UsagePurpose


class Out(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[str]
    rationale: str


async def test_structured_call_valid_output(mock_provider):
    mock_provider.queue("p", json.dumps({"items": ["a"], "rationale": "r"}))
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value == Out(items=["a"], rationale="r") and res.attempts == 1


async def test_structured_call_recovers_fenced_json(mock_provider):
    mock_provider.queue("p", "```json\n{\"items\": [], \"rationale\": \"ok\"}\n```")
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value is not None and res.value.rationale == "ok"


async def test_structured_call_retries_then_gives_up_on_invalid(mock_provider):
    mock_provider.queue("p", "not json at all")
    mock_provider.queue("p", json.dumps({"items": "wrong-type", "rationale": 1}))
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value is None and res.attempts == 2 and "invalid_output" in res.error


async def test_structured_call_retries_on_retryable_provider_error(mock_provider):
    mock_provider.queue("p", ProviderError("timeout", retryable=True))
    mock_provider.queue("p", json.dumps({"items": [], "rationale": "second try"}))
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value is not None and res.attempts == 2


async def test_structured_call_stops_on_non_retryable(mock_provider):
    mock_provider.queue("p", ProviderError("401", retryable=False))
    mock_provider.queue("p", json.dumps({"items": [], "rationale": "never"}))
    res = await structured_call(purpose="p", usage_purpose=UsagePurpose.exam_audit, system="s", user="u", schema=Out, ctx=CallContext())
    assert res.value is None and res.attempts == 1


def test_strictify_marks_all_required():
    schema = Out.model_json_schema()
    _strictify(schema)
    assert schema["additionalProperties"] is False and set(schema["required"]) == {"items", "rationale"}


@pytest.fixture
def provider():
    return OpenAICompatibleProvider(base_url="https://llm.test/v1", api_key="k", model="m", embed_model="e")


@respx.mock
async def test_openai_provider_chat_and_usage(provider):
    respx.post("https://llm.test/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"model": "m-1", "choices": [{"message": {"content": "{\"a\":1}"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 2}})
    )
    res = await provider.chat_json(purpose="p", system="s", user="u", json_schema={}, schema_name="X")
    assert res.content == '{"a":1}' and res.model == "m-1" and res.tokens_in == 5
    sent = json.loads(respx.calls.last.request.content)
    assert sent["response_format"]["type"] == "json_schema" and sent["temperature"] == 0.0
    assert respx.calls.last.request.headers["authorization"] == "Bearer k"


@respx.mock
async def test_openai_provider_error_classes(provider):
    route = respx.post("https://llm.test/v1/chat/completions")
    route.mock(return_value=httpx.Response(429))
    with pytest.raises(ProviderError) as e:
        await provider.chat_json(purpose="p", system="s", user="u", json_schema={}, schema_name="X")
    assert e.value.retryable
    route.mock(return_value=httpx.Response(400, json={"error": "bad"}))
    with pytest.raises(ProviderError) as e:
        await provider.chat_json(purpose="p", system="s", user="u", json_schema={}, schema_name="X")
    assert not e.value.retryable
    route.mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(ProviderError) as e:
        await provider.chat_json(purpose="p", system="s", user="u", json_schema={}, schema_name="X")
    assert "timed out" in str(e.value)


@respx.mock
async def test_openai_provider_embeddings(provider):
    respx.post("https://llm.test/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"model": "e", "data": [{"index": 1, "embedding": [0, 1]}, {"index": 0, "embedding": [1, 0]}]})
    )
    res = await provider.embed(["x", "y"])
    assert res.vectors == [[1.0, 0.0], [0.0, 1.0]]
