"""ATAR provider router — fallback across providers on failure."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from atar_models.model_events import ModelEvent
from atar_models.requests import ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth


class ProviderRouter:
    """Routes requests across providers with fallback on failure."""

    def __init__(self, providers: list[Any]) -> None:
        self.providers: list[Any] = providers
        self._fallback_count = 0

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Try providers in order until one succeeds."""
        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                result = await asyncio.wait_for(
                    provider.complete(request),
                    timeout=120,
                )
                if i > 0:
                    self._fallback_count += 1
                return result
            except TimeoutError:
                last_error = TimeoutError(f"{provider.model} timeout")
            except Exception as e:
                last_error = e
        raise RuntimeError(f"All providers failed. Last: {last_error}")

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        """Stream from providers with fallback on failure."""
        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                async for event in provider.stream(request):
                    yield event
                if i > 0:
                    self._fallback_count += 1
                return
            except Exception as e:
                last_error = e
        raise RuntimeError(f"All providers failed streaming. Last: {last_error}")

    @property
    def fallback_count(self) -> int:
        return self._fallback_count

    @property
    def model(self) -> str:
        return getattr(self.providers[0], "model", "router") if self.providers else "none"

    async def capabilities(self) -> ProviderCapabilities:
        if self.providers:
            return await self.providers[0].capabilities()
        return ProviderCapabilities(text=True, streaming=True, tools=True)

    async def list_models(self) -> list[str]:
        if self.providers:
            return await self.providers[0].list_models()
        return []

    async def count_tokens(self, request: TokenCountRequest) -> int:
        if self.providers:
            return await self.providers[0].count_tokens(request)
        return 0

    async def health_check(self) -> ProviderHealth:
        if self.providers:
            return await self.providers[0].health_check()
        return ProviderHealth(provider_id="router", status="unknown")


def create_router() -> ProviderRouter:
    """Create provider router from config with fallback chain."""
    import os

    from atar_provider_deepseek.client import DeepSeekProvider

    from atar_core.config_reader import get_api_key

    providers: list[Any] = []

    # Primary: DeepSeek
    key = get_api_key("deepseek") or os.environ.get("DEEPSEEK_API_KEY")
    if key:
        providers.append(DeepSeekProvider(api_key=key, model="deepseek-chat"))

    # Fallback: try Anthropic key
    key2 = get_api_key("anthropic") or os.environ.get("ANTHROPIC_API_KEY")
    if key2:
        from atar_provider_anthropic.client import AnthropicProvider
        providers.append(AnthropicProvider(api_key=key2, model="claude-sonnet-4-20250514"))

    if not providers:
        raise RuntimeError("No API keys configured. Run atar setup.")

    return ProviderRouter(providers)
