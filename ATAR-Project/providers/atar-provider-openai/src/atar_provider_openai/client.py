"""ATAR OpenAI-compatible provider base — shared streaming + tool calling logic.

Used by: OpenAI, DeepSeek, OpenRouter, Z.AI, Custom providers.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from atar_models.model_events import ModelEvent
from atar_models.requests import ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth


class OpenAICompatibleProvider:
    """Base for any provider with an OpenAI-compatible /v1/chat/completions endpoint."""

    api_key: str
    base_url: str
    model: str
    max_tokens: int
    _http: httpx.AsyncClient | None

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        env_key: str = "OPENAI_API_KEY",
    ) -> None:
        import os
        self.api_key = api_key or os.environ.get(env_key) or ""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self._http = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
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
        body = self._build_body(request, stream=False)
        timeout = min(getattr(request, "timeout", 120) or 120, 300)
        resp = await client.post(f"{self.base_url}/chat/completions", json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        text = msg.get("content") or ""
        tool_calls: list[dict[str, Any]] = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            try:
                inp = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError:
                inp = {}
            tool_calls.append({"id": tc.get("id", ""), "name": fn.get("name", ""), "input": inp})
        return ModelResponse(
            request_id=data.get("id", ""),
            model=data.get("model", ""),
            text=text,
            tool_calls=tool_calls,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        client = await self._get_client()
        body = self._build_body(request, stream=True)
        acc: dict[int, dict[str, Any]] = {}
        async with client.stream("POST", f"{self.base_url}/chat/completions", json=body) as resp:
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
                choice = data["choices"][0]
                delta = choice.get("delta", {})
                if delta.get("content"):
                    yield ModelEvent(event_type="text_delta", text=str(delta["content"]))
                tcs = delta.get("tool_calls") or []
                for tc in tcs:
                    idx = tc.get("index", 0)
                    if idx not in acc:
                        acc[idx] = {"id": "", "name": "", "arguments": ""}
                    entry = acc[idx]
                    if tc.get("id"):
                        entry["id"] = tc["id"]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        entry["name"] = fn["name"]
                    if fn.get("arguments"):
                        entry["arguments"] += fn["arguments"]
                if choice.get("finish_reason") == "tool_calls":
                    for idx in sorted(acc):
                        entry = acc[idx]
                        if entry["name"] and entry["arguments"]:
                            try:
                                parsed = json.loads(entry["arguments"])
                            except json.JSONDecodeError:
                                parsed = {}
                            yield ModelEvent(event_type="tool_call", provider_metadata={
                                "id": entry["id"], "name": entry["name"],
                                "input": parsed, "partial": False,
                            })

    async def count_tokens(self, request: TokenCountRequest) -> int:
        return 0

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_id="openai-compatible", status="unknown")

    def _build_body(self, request: ModelRequest, stream: bool) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        for msg in request.messages:
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {"id": tc["id"], "type": "function", "function": {
                        "name": tc["name"], "arguments": json.dumps(tc.get("input", {}))
                    }}
                    for tc in msg.tool_calls
                ]
                entry.pop("content", None)
            if msg.tool_call_id:
                entry["tool_call_id"] = msg.tool_call_id
            messages.append(entry)
        body: dict[str, Any] = {
            "model": request.model or self.model,
            "max_tokens": request.max_output_tokens or self.max_tokens,
            "messages": messages,
            "stream": stream,
        }
        if request.tools:
            body["tools"] = [
                {"type": "function", "function": {
                    "name": t.name, "description": t.description,
                    "parameters": t.parameters or {"type": "object", "properties": {}},
                }}
                for t in request.tools
            ]
            body["tool_choice"] = "auto"
        return body
