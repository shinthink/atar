"""ATAR request models — normalized per Section 6.7."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    type: str
    text: str | None = None


class Message(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ToolSchema(BaseModel):
    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ReasoningOptions(BaseModel):
    effort: str = "medium"
    budget_tokens: int | None = None


class ModelRequest(BaseModel):
    request_id: UUID = Field(default_factory=uuid4)
    provider_id: str = ""
    model: str = ""
    messages: list[Message] = Field(default_factory=list)
    system: list[ContentBlock] = Field(default_factory=list)
    tools: list[ToolSchema] = Field(default_factory=list)
    cache_system: bool = True  # Mark system prompt as cacheable
    cache_tools: bool = True   # Mark tool definitions as cacheable
    tool_choice: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    reasoning: ReasoningOptions | None = None
    response_format: dict[str, Any] | None = None
    stop: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: float = 120.0


class TokenCountRequest(BaseModel):
    model: str
    messages: list[Message] = Field(default_factory=list)
    system: str = ""
