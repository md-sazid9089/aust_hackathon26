from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.schemas import ApiModel


class ChatMessage(ApiModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ToolCall(ApiModel):
    """One planned tool invocation. `arguments` is a JSON object encoded as a string (strict-schema friendly)."""

    tool: str
    arguments: str = Field(description='JSON object string, e.g. {"course_id": "..."}')


class AssistantPlan(ApiModel):
    """LLM output for one planning round."""

    thought: str = Field(description="One sentence: what the user wants and what you will do next")
    tool_calls: list[ToolCall] = Field(description="Tools to run now, in order. Empty when you can answer directly.")
    reply: str = Field(description="Final Markdown reply to the user (used only when tool_calls is empty)")


class ActionOut(ApiModel):
    tool: str
    status: Literal["ok", "error"]
    summary: str
    data: dict[str, Any] | None = None


class ChatResponse(ApiModel):
    reply: str
    actions: list[ActionOut] = Field(default_factory=list)
    navigate: str | None = Field(None, description="Frontend route the UI may offer to open")
    model: str | None = None
