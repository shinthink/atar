"""ATAR Ollama provider — local LLM with zero API key requirement.

Auto-detects local Ollama instance. Falls back gracefully when unavailable.
Users can run ATAR with zero setup: install Ollama, pull a model, run atar.
"""

from __future__ import annotations

import json
from typing import Any

from atar_models.model_events import ModelEvent
from atar_models.requests import Message, ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth
from atar_protocols import ModelProvider


class OllamaProvider(ModelProvider):
    """Local LLM via Ollama — zero API key required."""

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    @property
    def display_name(self) -> str:
        return f"Ollama ({self.model})"

    async def complete(self, request: ModelRequest) -> ModelResponse:
        try:
            import httpx
            payload = {
                "model": self.model,
                "messages": self._format_messages(request.messages),
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            return ModelResponse(
                final_text=data.get("message", {}).get("content", ""),
                provider_id="ollama",
                model=self.model,
            )
        except httpx.ConnectError:
            return ModelResponse(
                final_text="",
                provider_id="ollama",
                error="Cannot connect to Ollama. Is it running? Run: ollama serve",
            )
        except Exception as e:
            return ModelResponse(final_text="", provider_id="ollama", error=str(e))

    async def stream(self, request: ModelRequest) -> Any:
        try:
            import httpx
            payload = {
                "model": self.model,
                "messages": self._format_messages(request.messages),
                "stream": True,
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(120)) as client, client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield ModelEvent(event_type="text_delta", text=content)
                        if data.get("done"):
                            yield ModelEvent(event_type="done")
                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError:
            yield ModelEvent(event_type="error", error="Cannot connect to Ollama. Is it running? Run: ollama serve")
        except Exception as e:
            yield ModelEvent(event_type="error", error=str(e))

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            text=True,
            streaming=True,
            tools=False,  # Ollama tool support varies by model
            vision=False,
            max_context=8192,
        )

    async def list_models(self) -> list[str]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    async def count_tokens(self, request: TokenCountRequest) -> int:
        # Ollama doesn't have a token count endpoint
        return sum(len(m.get("content", "")) // 4 for m in request.messages)

    async def health_check(self) -> ProviderHealth:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=httpx.Timeout(5)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    return ProviderHealth(provider_id="ollama", status="healthy")
                return ProviderHealth(provider_id="ollama", status="degraded")
        except Exception:
            return ProviderHealth(provider_id="ollama", status="unavailable")

    def _format_messages(self, messages: list[Message]) -> list[dict]:
        formatted = []
        for m in messages:
            role = getattr(m, "role", "user")
            content = getattr(m, "content", "")
            msg = {"role": role, "content": content}
            if hasattr(m, "tool_calls") and m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if hasattr(m, "tool_call_id") and m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            formatted.append(msg)
        return formatted


def is_ollama_available() -> bool:
    """Quick check if Ollama is running locally."""
    try:
        import asyncio

        import httpx

        async def _check():
            async with httpx.AsyncClient(timeout=httpx.Timeout(3)) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                return resp.status_code == 200

        return asyncio.run(_check())
    except Exception:
        return False


def get_ollama_provider() -> OllamaProvider | None:
    """Get an Ollama provider if available, auto-detecting best model."""
    if not is_ollama_available():
        return None

    # Try common models in order of preference
    preferred = ["llama3.2", "mistral", "qwen2.5", "gemma2", "phi3", "llama3"]
    available = []

    try:
        import asyncio

        import httpx

        async def _list():
            async with httpx.AsyncClient(timeout=httpx.Timeout(5)) as client:
                resp = await client.get("http://localhost:11434/api/tags")
                return [m["name"] for m in resp.json().get("models", [])]

        available = asyncio.run(_list())
    except Exception:
        pass

    for model in preferred:
        if model in available or any(model in m for m in available):
            return OllamaProvider(model=model)

    # Use first available model
    if available:
        return OllamaProvider(model=available[0])

    # Default — user will need to pull a model
    return OllamaProvider(model="llama3.2")
