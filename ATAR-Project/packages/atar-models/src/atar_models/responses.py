"""ATAR response models — normalized provider responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0


class ModelResponse(BaseModel):
    request_id: str = ""
    model: str = ""
    text: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: Usage | None = None
    finish_reason: str = "stop"
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(BaseModel):
    text: bool = True
    streaming: bool = False
    tools: bool = False
    parallel_tools: bool = False
    reasoning: bool = False
    vision: bool = False
    audio_input: bool = False
    audio_output: bool = False
    files: bool = False
    structured_output: bool = False
    token_counting: bool = False
    model_listing: bool = False
    prompt_caching: bool = False
    request_id: bool = False


class ProviderHealth(BaseModel):
    provider_id: str = ""
    status: str = "unknown"
    latency_ms: float = 0.0
    error: str | None = None
    last_checked: str = ""
