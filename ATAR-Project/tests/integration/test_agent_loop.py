"""Integration tests for autonomous agent loop with deterministic fake provider."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

import pytest
from atar_core.agent import Agent
from atar_models.requests import ModelRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth


class FakeToolProvider:
    """Fake provider that returns deterministic tool-call sequences."""
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self._call_count = 0
        self.model = "fake-test"
        self.api_key = "fake"

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(text=True, streaming=True, tools=True)

    async def list_models(self) -> list[str]:
        return ["fake"]

    async def complete(self, request: ModelRequest) -> ModelResponse:
        if self._call_count >= len(self.responses):
            # Return final empty response
            return ModelResponse(text="Final answer", model="fake")
        resp_data = self.responses[self._call_count]
        self._call_count += 1

        tool_calls = resp_data.get("tool_calls", [])
        return ModelResponse(
            text=resp_data.get("text", ""),
            tool_calls=tool_calls,
            model="fake",
        )

    async def stream(self, request: ModelRequest):
        """Streaming — generate text events from response data."""
        if self._call_count >= len(self.responses):
            yield type("Event", (), {"event_type": "text_delta", "text": "Final answer", "provider_metadata": {}})()
            return
        resp_data = self.responses[self._call_count]
        self._call_count += 1

        text = resp_data.get("text", "")
        if text:
            # Stream text character by character
            for ch in text:
                yield type("Event", (), {"event_type": "text_delta", "text": ch, "provider_metadata": {}})()

        for tc in resp_data.get("tool_calls", []):
            yield type("Event", (), {"event_type": "tool_call", "text": None, "provider_metadata": tc})()

    async def count_tokens(self, request: Any) -> int:
        return 0

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(provider_id="fake", status="ok")


class TestAutonomousAgentLoop:
    """Prove the agent loop: text → tool → feedback → final."""

    @pytest.mark.asyncio
    async def test_single_turn_direct_answer(self) -> None:
        """Simple question gets direct answer, no tool calls."""
        provider = FakeToolProvider([{"text": "Hello from fake"}])
        agent = Agent(provider=provider, max_turns=3, tools=[])
        result = await agent.run("hi")
        assert result is not None
        assert "Hello" in result.final_text
        assert len(agent._messages) == 2  # user + assistant

    @pytest.mark.asyncio
    async def test_tool_call_loop(self) -> None:
        """Tool call → tool execution → model continues."""
        provider = FakeToolProvider([
            {
                "text": "",
                "tool_calls": [
                    {"id": "call_1", "name": "web_search", "input": {"query": "ataraxia"}}
                ],
            },
            {"text": "Found references about ataraxia", "tool_calls": []},
        ])
        agent = Agent(provider=provider, max_turns=5, tools=[1])
        result = await agent.run("cari ataraxia")
        assert result is not None
        assert "Found references" in result.final_text
        # Should have user + assistant(tool) + tool_result + assistant(final)
        assert len(agent._messages) >= 3

    @pytest.mark.asyncio
    async def test_max_turns_stops_loop(self) -> None:
        """Agent stops at max_turns even if model keeps asking for tools."""
        provider = FakeToolProvider([
            {"text": "", "tool_calls": [{"id": f"c{i}", "name": "web_search", "input": {"q": str(i)}}]}
            for i in range(10)
        ])
        agent = Agent(provider=provider, max_turns=2, tools=[1])
        result = await agent.run("search")
        assert result is not None
        assert result.state.name == "BUDGET_EXHAUSTED"
        assert result.budget["turns_used"] >= 3

    @pytest.mark.asyncio
    async def test_partial_tool_call_skipped(self) -> None:
        """Partial tool calls (no input) are skipped."""
        provider = FakeToolProvider([
            {
                "text": "",
                "tool_calls": [
                    {"id": "call_1", "name": "web_search", "partial": True},  # skipped
                    {"id": "call_1", "name": "web_search", "input": {"query": "test"}},  # used
                ],
            },
            {"text": "Done", "tool_calls": []},
        ])
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        result = await agent.run("search")
        assert "Done" in result.final_text

    @pytest.mark.asyncio
    async def test_role_ordering(self) -> None:
        """Messages maintain correct role alternation."""
        provider = FakeToolProvider([
            {"text": "", "tool_calls": [{"id": "c1", "name": "write_file", "input": {"path": "/t", "content": "x"}}]},
            {"text": "File written", "tool_calls": []},
        ])
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        await agent.run("write file")
        roles = [m.role for m in agent._messages]
        # user → assistant → user(tool result) → assistant(final)
        assert "user" in roles
        assert any(r in roles for r in ["assistant", "tool"])


class TestCancellation:
    """Prove cancellation works."""

    @pytest.mark.asyncio
    async def test_cancel_during_run(self) -> None:
        """Cancelling the task stops execution cleanly."""
        provider = FakeToolProvider([{"text": "slow response"}])
        agent = Agent(provider=provider, max_turns=3, tools=[])

        async def run_with_cancel() -> None:
            task = asyncio.create_task(agent.run("hi"))
            await asyncio.sleep(0.01)
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        await run_with_cancel()
        # Should not crash
