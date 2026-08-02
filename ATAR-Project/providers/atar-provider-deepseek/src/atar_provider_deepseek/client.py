"""ATAR DeepSeek provider via OpenAI-compatible API — supports tool calling."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from atar_models.model_events import ModelEvent
from atar_models.requests import ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth


class DeepSeekProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        max_tokens: int = 4096,
    ) -> None:
        import os
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY") or ""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self._http: httpx.AsyncClient | None = None

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
        resp = await client.post(f"{self.base_url}/chat/completions", json=body)
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        text = msg.get("content") or ""
        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "input": json.loads(fn.get("arguments", "{}")),
            })
        return ModelResponse(
            request_id=data.get("id", ""),
            model=data.get("model", ""),
            text=text,
            tool_calls=tool_calls,
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        client = await self._get_client()
        body = self._build_body(request, stream=True)
        tool_id = ""
        tool_name = ""
        tool_args = ""
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
                delta = data["choices"][0].get("delta", {})
                if delta.get("content"):
                    yield ModelEvent(event_type="text_delta", text=str(delta["content"]))
                tc = delta.get("tool_calls")
                if tc:
                    fn = tc[0].get("function", {}) if tc else {}
                    if tc[0].get("id"):
                        tool_id = tc[0]["id"]
                    if fn.get("name"):
                        tool_name = fn["name"]
                        yield ModelEvent(event_type="tool_call", provider_metadata={"id": tool_id, "name": tool_name, "partial": True})
                    if fn.get("arguments"):
                        tool_args += fn["arguments"]
                if data["choices"][0].get("finish_reason") == "tool_calls" and tool_name:
                    try:
                        parsed = json.loads(tool_args)
                    except json.JSONDecodeError:
                        parsed = {}
                    yield ModelEvent(event_type="tool_call", provider_metadata={"id": tool_id, "name": tool_name, "input": parsed, "partial": False})

    async def count_tokens(self, request: TokenCountRequest) -> int:
        return 0

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_id="deepseek", status="unknown")

    def _build_body(self, request: ModelRequest, stream: bool) -> dict[str, Any]:
        messages: list[dict[str, Any]] = []
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
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
