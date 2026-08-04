"""ATAR Custom provider — user-configured OpenAI-compatible endpoint."""

from __future__ import annotations

import os

from atar_provider_openai.client import OpenAICompatibleProvider


class CustomProvider(OpenAICompatibleProvider):
    """Custom provider for self-hosted or third-party OpenAI-compatible endpoints."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url or os.environ.get("CUSTOM_API_BASE", "http://localhost:8000/v1"),
            model=model or os.environ.get("CUSTOM_MODEL", "local-model"),
            max_tokens=max_tokens,
            env_key="CUSTOM_API_KEY",
        )
