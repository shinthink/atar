"""ATAR OpenRouter provider."""

from __future__ import annotations

from atar_provider_openai.client import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter provider — OpenAI-compatible with model routing."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "deepseek/deepseek-v4-flash",
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=max_tokens,
            env_key="OPENROUTER_API_KEY",
        )
