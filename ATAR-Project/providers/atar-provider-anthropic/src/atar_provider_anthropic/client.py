"""ATAR Anthropic provider — Messages API + SSE streaming.

Also works with DeepSeek Anthropic-compatible endpoint.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from atar_models.model_events import ModelEvent
from atar_models.requests import ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth


class AnthropicProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self._http: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._http

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(text=True, streaming=True, tools=True)

    async def list_models(self) -> list[str]:
        return [self.model]

    async def complete(self, request: ModelRequest) -> ModelResponse:
        client = await self._get_client()
        body = _build_body(request, self.model, self.max_tokens, stream=False)
        resp = await client.post(f"{self.base_url}/messages", json=body)
        resp.raise_for_status()
        return _parse_response(resp.json())

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        client = await self._get_client()
        body = _build_body(request, self.model, self.max_tokens, stream=True)
        async with client.stream("POST", f"{self.base_url}/messages", json=body) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                yield _parse_event(data)

    async def count_tokens(self, request: TokenCountRequest) -> int:
        client = await self._get_client()
        body = {
            "model": request.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
        }
        resp = await client.post(f"{self.base_url}/messages/count_tokens", json=body)
        resp.raise_for_status()
        return resp.json().get("input_tokens", 0)

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_id="anthropic", status="unknown")


# ── helpers ──

def _build_body(
    request: ModelRequest, model: str, max_tokens: int, *, stream: bool
) -> dict[str, Any]:
    system = ""
    messages: list[dict[str, Any]] = []
    for msg in request.messages:
        if msg.role == "system":
            system = msg.content
        else:
            messages.append({"role": msg.role, "content": msg.content})

    body: dict[str, Any] = {
        "model": request.model or model,
        "max_tokens": request.max_output_tokens or max_tokens,
        "messages": messages,
        "stream": stream,
    }
    if system:
        body["system"] = system
    if request.temperature is not None:
        body["temperature"] = request.temperature
    if request.tools:
        body["tools"] = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters or {}}
            for t in request.tools
        ]
        body["tool_choice"] = {"type": "auto"}
    return body


def _parse_response(data: dict[str, Any]) -> ModelResponse:
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += str(block.get("text", ""))
        # skip thinking blocks
    return ModelResponse(
        request_id=str(data.get("id", "")),
        model=str(data.get("model", "")),
        text=text,
    )


def _parse_event(data: dict[str, Any]) -> ModelEvent:
    etype = data.get("type", "")
    if etype == "content_block_delta":
        delta = data.get("delta", {})
        dtype = delta.get("type", "")
        if dtype == "text_delta":
            return ModelEvent(event_type="text_delta", text=str(delta.get("text", "")))
        if dtype == "thinking_delta":
            return ModelEvent(event_type="thinking", text="")
    if etype == "content_block_start":
        cblock = data.get("content_block", {})
        if cblock.get("type") == "thinking":
            return ModelEvent(event_type="thinking", text="")
    if etype == "content_block_stop":
        return ModelEvent(event_type="thinking", text="")
    if etype == "message_start":
        return ModelEvent(event_type="message_start", provider_metadata=data.get("message", {}))
    if etype == "message_stop":
        return ModelEvent(event_type="response_completed", finish_reason="stop")
    return ModelEvent(event_type="stream_event", provider_metadata=data)
