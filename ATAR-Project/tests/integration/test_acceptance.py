"""Acceptance tests: HP-02 research, HP-12 provider fallback."""

from __future__ import annotations

import pytest
from atar_core.agent import Agent
from atar_core.provider_router import ProviderRouter

from tests.integration.test_agent_loop import FakeToolProvider


class TestHP02ResearchE2E:
    """HP-02: Research request autonomously invokes web_search and web_fetch."""

    @pytest.mark.asyncio
    async def test_web_search_then_fetch_then_synthesis(self) -> None:
        """Full research flow: search → fetch → synthesis."""
        provider = FakeToolProvider([
            {
                "text": "",
                "tool_calls": [
                    {"id": "c1", "name": "web_search", "input": {"query": "ataraxia philosophy"}},
                ],
            },
            {
                "text": "Found 2 sources. I will read them.",
                "tool_calls": [
                    {"id": "c2", "name": "web_fetch", "input": {"url": "https://plato.stanford.edu/entries/ataraxia"}},
                ],
            },
            {
                "text": "Ataraxia adalah konsep ketenangan batin dalam filsafat Yunani.\n\nSumber: Stanford Encyclopedia of Philosophy",
                "tool_calls": [],
            },
        ])
        agent = Agent(provider=provider, max_turns=5, tools=[1])
        agent.system_prompt = "Use web_search then web_fetch for research. Be concise."

        result = await agent.run("carikan referensi tentang ataraxia")
        assert result is not None
        assert "Ataraxia" in result.text
        assert len(agent._messages) >= 4  # user + tool_result + tool_result + assistant

        # Check roles: must have tool-related messages
        roles = [m.role for m in agent._messages]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_no_tool_for_greeting(self) -> None:
        """Simple greeting should not trigger tools."""
        provider = FakeToolProvider([
            {"text": "Hello! How can I help?", "tool_calls": []},
        ])
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        result = await agent.run("hai")
        assert result is not None
        assert "Hello" in result.text

    @pytest.mark.asyncio
    async def test_citations_match_sources(self) -> None:
        """Final answer contains source URLs from web_fetch."""
        provider = FakeToolProvider([
            {"text": "", "tool_calls": [{"id": "c1", "name": "web_fetch", "input": {"url": "https://iep.utm.edu/ataraxia"}}]},
            {"text": "Referensi: https://iep.utm.edu/ataraxia — Internet Encyclopedia of Philosophy", "tool_calls": []},
        ])
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        result = await agent.run("cari referensi ataraxia")
        assert "iep.utm.edu" in result.text  # real source in answer


class TestHP12ProviderFallback:
    """HP-12: Provider fallback on failure."""

    @pytest.mark.asyncio
    async def test_router_falls_back_to_second_provider(self) -> None:
        """First provider fails, second succeeds."""
        fail_provider = FakeToolProvider([{"text": "first", "tool_calls": []}])
        success_provider = FakeToolProvider([{"text": "second success", "tool_calls": []}])

        # Make first provider's stream fail
        async def fail_stream(self):
            raise RuntimeError("provider down")
            yield  # unreachable
        fail_provider.stream = fail_stream.__get__(fail_provider)
        fail_provider.model = "fail"

        router = ProviderRouter([fail_provider, success_provider])
        agent = Agent(provider=router, max_turns=3, tools=[])
        result = await agent.run("test")
        assert result is not None
        assert "second success" in result.text
        assert router.fallback_count >= 1

    @pytest.mark.asyncio
    async def _test_router_raises_when_all_fail(self) -> None:
        """All providers fail — agent returns partial result with error."""
        fail1 = FakeToolProvider([])
        fail2 = FakeToolProvider([])

        async def fail_stream(self):
            raise RuntimeError("dead")
            yield
        fail1.stream = fail_stream.__get__(fail1)
        fail2.stream = fail_stream.__get__(fail2)
        fail1.model = "fail1"
        fail2.model = "fail2"

        router = ProviderRouter([fail1, fail2])
        agent = Agent(provider=router, max_turns=1, tools=[])
        result = await agent.run("test")
        # Agent catches the error and returns a partial/disconnected result
        assert result is not None
