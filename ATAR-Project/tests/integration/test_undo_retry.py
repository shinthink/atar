"""F1: /retry and /undo tests."""

from __future__ import annotations

import pytest
from atar_core.agent import Agent, StreamCallbacks


class FakeSimpleProvider:
    def __init__(self) -> None:
        self.model = "fake"

    async def stream(self, request):
        yield type("E", (), {"event_type": "text_delta", "text": "response", "provider_metadata": {}})()

    async def count_tokens(self, request):
        return 0

    async def health_check(self):
        return type("H", (), {"provider_id": "fake", "status": "ok"})()


class TestUndoRetry:
    """Verify undo and retry behavior."""

    @pytest.mark.asyncio
    async def test_undo_empty_history_no_crash(self) -> None:
        """Undo on empty history returns None, no crash."""
        agent = Agent(provider=FakeSimpleProvider())
        result = agent.undo_last_turn()
        assert result is None

    @pytest.mark.asyncio
    async def test_undo_removes_last_turn(self) -> None:
        """Undo removes user + assistant + tool results."""
        agent = Agent(provider=FakeSimpleProvider())
        await agent.run("hello")
        before = len(agent._messages)
        text = agent.undo_last_turn()
        after = len(agent._messages)
        assert text is not None
        assert after < before

    @pytest.mark.asyncio
    async def test_undo_tool_turn_removes_all(self) -> None:
        """Undo on a turn with tool calls removes everything properly."""
        agent = Agent(provider=FakeSimpleProvider())
        # Simulate a turn: user -> assistant(tool_call) -> tool result
        from atar_models.requests import Message
        agent._messages = [
            Message(role="system", content="test"),
            Message(role="user", content="search"),
            Message(role="assistant", content=None, tool_calls=[{"id": "1", "name": "web_search", "input": {"q": "x"}}]),
            Message(role="tool", content="result", tool_call_id="1"),
        ]
        assert len(agent._messages) == 4
        text = agent.undo_last_turn()
        assert text == "search"
        assert len(agent._messages) == 1  # only system remains

    @pytest.mark.asyncio
    async def test_retry_returns_last_user_message(self) -> None:
        """Retry returns the last user message for in-place regenerate."""
        from atar_models.requests import Message
        agent = Agent(provider=FakeSimpleProvider())
        agent._messages = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi there"),
        ]
        last = agent.retry_last_turn()
        assert last == "hello"

    @pytest.mark.asyncio
    async def test_retry_empty_history(self) -> None:
        """Retry on empty history returns None."""
        agent = Agent(provider=FakeSimpleProvider())
        assert agent.retry_last_turn() is None
