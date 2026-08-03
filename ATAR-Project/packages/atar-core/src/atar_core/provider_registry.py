"""ATAR provider registry — profiles, discovery, credential mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ProviderProfile:
    """Metadata for an AI provider."""
    id: str                          # "deepseek"
    display_name: str                # "DeepSeek"
    base_url: str                    # "https://api.deepseek.com/v1"
    env_key: str                     # "DEEPSEEK_API_KEY"
    default_model: str               # "deepseek-chat"
    default_models: list[str] = field(default_factory=list)
    api_mode: str = "openai-compatible"  # openai, anthropic, openai-compatible
    auth_header: str = "Bearer"      # Bearer, x-api-key
    model_discovery: bool = False

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.env_key)


# All supported providers with correct profiles
PROVIDERS: dict[str, ProviderProfile] = {
    "deepseek": ProviderProfile(
        id="deepseek",
        display_name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        env_key="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        default_models=["deepseek-chat", "deepseek-reasoner"],
        api_mode="openai-compatible",
    ),
    "openai": ProviderProfile(
        id="openai",
        display_name="OpenAI",
        base_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
        default_model="gpt-4o",
        default_models=["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        api_mode="openai",
    ),
    "anthropic": ProviderProfile(
        id="anthropic",
        display_name="Anthropic",
        base_url="https://api.anthropic.com/v1",
        env_key="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-20250514",
        default_models=["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
        api_mode="anthropic",
        auth_header="x-api-key",
    ),
    "openrouter": ProviderProfile(
        id="openrouter",
        display_name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        default_model="deepseek/deepseek-chat",
        default_models=["deepseek/deepseek-chat", "anthropic/claude-sonnet-4"],
        api_mode="openai-compatible",
    ),
    "zai": ProviderProfile(
        id="zai",
        display_name="Z.AI",
        base_url="https://api.z.ai/api/v1",
        env_key="ZAI_API_KEY",
        default_model="z-ai-model",
        default_models=[],
        api_mode="openai-compatible",
    ),
    "custom": ProviderProfile(
        id="custom",
        display_name="Custom",
        base_url=os.environ.get("CUSTOM_API_BASE", "http://localhost:8000/v1"),
        env_key="CUSTOM_API_KEY",
        default_model=os.environ.get("CUSTOM_MODEL", "local-model"),
        default_models=[],
        api_mode="openai-compatible",
    ),
}


def get_provider(provider_id: str) -> ProviderProfile | None:
    return PROVIDERS.get(provider_id)


def list_providers() -> list[ProviderProfile]:
    return list(PROVIDERS.values())


def list_available() -> list[ProviderProfile]:
    """Return providers with valid API keys set."""
    return [p for p in PROVIDERS.values() if p.api_key]
