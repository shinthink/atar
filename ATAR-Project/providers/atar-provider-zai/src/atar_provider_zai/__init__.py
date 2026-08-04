"""ATAR Z.AI provider."""

from __future__ import annotations

from atar_provider_openai.client import OpenAICompatibleProvider


class ZAIProvider(OpenAICompatibleProvider):
    """Z.AI provider — OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.z.ai/api/v1",
        model: str = "z-ai-model",
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=max_tokens,
            env_key="ZAI_API_KEY",
        )
