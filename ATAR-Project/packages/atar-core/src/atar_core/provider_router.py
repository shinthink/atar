"""ATAR provider router — fallback across providers on failure."""

from __future__ import annotations

import asyncio
from typing import Any

from atar_models.requests import ModelRequest
from atar_models.responses import ModelResponse


class ProviderRouter:
    """Routes requests across providers with fallback on failure."""

    def __init__(self, providers: list[Any]) -> None:
        self.providers = providers
        self._fallback_count = 0

    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Try providers in order until one succeeds."""
        last_error = None
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

    async def stream(self, request: ModelRequest):
        """Stream from first available provider — no fallback for streaming yet."""
        if not self.providers:
            raise RuntimeError("No providers available")
        provider = self.providers[0]
        async for event in provider.stream(request):
            yield event

    @property
    def fallback_count(self) -> int:
        return self._fallback_count


def create_router() -> ProviderRouter:
    """Create provider router from config with fallback chain."""
    import os

    from atar_provider_deepseek.client import DeepSeekProvider

    from atar_core.config_reader import get_api_key

    providers = []

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
