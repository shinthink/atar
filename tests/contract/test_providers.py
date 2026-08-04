"""Contract tests for OpenAI-compatible provider base and concrete implementations."""

from __future__ import annotations

import pytest
from atar_provider_custom import CustomProvider
from atar_provider_openai import OpenAIProvider
from atar_provider_openai.client import OpenAICompatibleProvider
from atar_provider_openrouter import OpenRouterProvider
from atar_provider_zai import ZAIProvider


class TestOpenAICompatibleProvider:
    """Base provider contract."""

    def test_init_defaults(self) -> None:
        p = OpenAICompatibleProvider(api_key="sk-test")
        assert p.api_key == "sk-test"
        assert p.base_url == "https://api.openai.com/v1"
        assert p.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_capabilities(self) -> None:
        p = OpenAICompatibleProvider(api_key="sk-test")
        caps = await p.capabilities()
        assert caps.text is True
        assert caps.streaming is True
        assert caps.tools is True

    @pytest.mark.asyncio
    async def test_list_models(self) -> None:
        p = OpenAICompatibleProvider(api_key="sk-test", model="gpt-5.6")
        models = await p.list_models()
        assert "gpt-5.6" in models

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        p = OpenAICompatibleProvider(api_key="sk-test")
        health = await p.health_check()
        assert health.provider_id == "openai-compatible"
        assert health.status == "unknown"

    @pytest.mark.asyncio
    async def test_count_tokens(self) -> None:
        from atar_models.requests import Message, TokenCountRequest

        p = OpenAICompatibleProvider(api_key="sk-test")
        req = TokenCountRequest(
            provider_id="openai",
            model="gpt-4o",
            messages=[Message(role="user", content="hello")],
        )
        count = await p.count_tokens(req)
        assert count >= 0

    def test_build_body_basic(self) -> None:
        from atar_models.requests import Message, ModelRequest

        p = OpenAICompatibleProvider(api_key="sk-test")
        req = ModelRequest(
            provider_id="openai",
            model="gpt-4o",
            messages=[Message(role="user", content="hello")],
        )
        body = p._build_body(req, stream=False)
        assert body["model"] == "gpt-4o"
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "hello"
        assert body["stream"] is False

    def test_build_body_with_tool_calls(self) -> None:
        from atar_models.requests import Message, ModelRequest

        p = OpenAICompatibleProvider(api_key="sk-test")
        req = ModelRequest(
            provider_id="openai",
            model="gpt-4o",
            messages=[
                Message(role="assistant", content=None, tool_calls=[
                    {"id": "c1", "name": "read_file", "input": {"path": "/tmp/test"}}
                ]),
            ],
        )
        body = p._build_body(req, stream=True)
        assert len(body["messages"][0]["tool_calls"]) == 1
        assert body["messages"][0]["tool_calls"][0]["function"]["name"] == "read_file"
        assert body["stream"] is True

    def test_build_body_with_tool_schemas(self) -> None:
        from atar_models.requests import Message, ModelRequest, ToolSchema

        p = OpenAICompatibleProvider(api_key="sk-test")
        tool = ToolSchema(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {"x": {"type": "string"}}},
        )
        req = ModelRequest(
            provider_id="openai",
            model="gpt-4o",
            messages=[Message(role="user", content="test")],
            tools=[tool],
        )
        body = p._build_body(req, stream=False)
        assert "tools" in body
        assert body["tools"][0]["function"]["name"] == "test_tool"
        assert body["tool_choice"] == "auto"


class TestConcreteProviders:
    """Each concrete provider should instantiate with correct defaults."""

    def test_openai_provider(self) -> None:
        p = OpenAIProvider(api_key="sk-test")
        assert p.base_url == "https://api.openai.com/v1"
        assert p.model == "gpt-4o"

    def test_openrouter_provider(self) -> None:
        p = OpenRouterProvider(api_key="sk-test")
        assert p.base_url == "https://openrouter.ai/api/v1"
        assert "deepseek" in p.model

    def test_zai_provider(self) -> None:
        p = ZAIProvider(api_key="sk-test")
        assert "z.ai" in p.base_url

    def test_custom_provider(self) -> None:
        p = CustomProvider(api_key="sk-test", base_url="https://my-api.example.com/v1", model="custom-model")
        assert p.base_url == "https://my-api.example.com/v1"
        assert p.model == "custom-model"

    def test_custom_provider_env_fallback(self) -> None:
        import os

        os.environ["CUSTOM_API_BASE"] = "https://env-api.example.com/v1"
        os.environ["CUSTOM_MODEL"] = "env-model"
        try:
            p = CustomProvider()
            assert p.base_url == "https://env-api.example.com/v1"
            assert p.model == "env-model"
        finally:
            del os.environ["CUSTOM_API_BASE"]
            del os.environ["CUSTOM_MODEL"]

    @pytest.mark.asyncio
    async def test_all_have_capabilities(self) -> None:
        providers = [
            OpenAIProvider(api_key="sk-test"),
            OpenRouterProvider(api_key="sk-test"),
            ZAIProvider(api_key="sk-test"),
            CustomProvider(api_key="sk-test"),
        ]
        for p in providers:
            caps = await p.capabilities()
            assert caps.text is True
            assert caps.tools is True
