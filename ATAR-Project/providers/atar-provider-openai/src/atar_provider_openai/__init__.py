"""ATAR OpenAI provider."""

from __future__ import annotations

from atar_provider_openai.client import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider using native /v1/chat/completions."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=max_tokens,
            env_key="OPENAI_API_KEY",
        )
