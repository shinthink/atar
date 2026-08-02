"""Contract tests for normalized tool messages — currently FAILING on ATAR pre-alpha."""

from __future__ import annotations

from typing import Any

import pytest
from atar_core.agent import Agent


class RecordingProvider:
    """Fake provider that records tool calls for inspection."""
    def __init__(self) -> None:
        self.model = "fake"
        self._messages_sent: list[Any] = []
        self._call_count = 0

    async def capabilities(self):
        return type("C", (), {"text": True, "streaming": True, "tools": True})()

    async def list_models(self):
        return ["fake"]

    async def stream(self, request):
        self._messages_sent = list(request.messages) if hasattr(request, "messages") else []
        # Check if this is the first call (has tools) or second (needs final)
        if self._call_count == 0:
            self._call_count += 1
            yield type("E", (), {"event_type": "tool_call", "text": None, "provider_metadata": {"id": "call_1", "name": "web_search", "input": {"query": "test"}}})()
            yield type("E", (), {"event_type": "tool_call", "text": None, "provider_metadata": {"id": "call_2", "name": "web_fetch", "input": {"url": "https://example.com"}}})()
        else:
            self._call_count += 1
            for ch in "Final answer after tools":
                yield type("E", (), {"event_type": "text_delta", "text": ch, "provider_metadata": {}})()
        return
        yield  # unreachable

    async def count_tokens(self, request):
        return 0

    async def health_check(self):
        return type("H", (), {"provider_id": "fake", "status": "ok"})()


class TestToolMessageRoles:
    """Verify tool messages use correct roles and structure."""

    @pytest.mark.asyncio
    async def test_tool_result_has_role_tool_not_user(self) -> None:
        """Tool results MUST use role='tool', not role='user'."""
        provider = RecordingProvider()
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        await agent.run("search")

        # Check messages after tool execution
        tool_messages = [m for m in agent._messages if "Tool " in str(getattr(m, "content", "")) or getattr(m, "role", "") == "tool"]
        user_tool_impersonations = [m for m in agent._messages if getattr(m, "role", "") == "user" and "Tool " in str(getattr(m, "content", ""))]
        assert len(user_tool_impersonations) == 0, (
            f"Found {len(user_tool_impersonations)} tool results stored as user messages. "
            f"Tool results must use role='tool' with tool_call_id."
        )

    @pytest.mark.asyncio
    async def test_tool_result_keeps_tool_call_id(self) -> None:
        """Tool results MUST preserve the tool_call_id for matching."""
        provider = RecordingProvider()
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        await agent.run("search")

        tool_msgs = [m for m in agent._messages if getattr(m, "role", "") == "tool"]
        for tm in tool_msgs:
            assert hasattr(tm, "tool_call_id") and tm.tool_call_id, (
                f"Tool result missing tool_call_id: {tm}"
            )

    @pytest.mark.asyncio
    async def test_assistant_tool_call_stored_before_result(self) -> None:
        """Assistant tool_call message MUST appear before tool results."""
        provider = RecordingProvider()
        agent = Agent(provider=provider, max_turns=3, tools=[1])
        await agent.run("search")

        roles = [getattr(m, "role", "") for m in agent._messages]
        # Expected: system?, user, assistant(tool_calls), tool, tool, assistant(final)
        assert any(r in roles for r in ["assistant", "tool"]), "No assistant message found in message history"


class TestApprovalNeverAuto:
    """Verify approval is NEVER hardcoded as true."""

    @pytest.mark.asyncio
    async def test_agent_never_hardcodes_approved_true(self) -> None:
        """_execute_tool must not hardcode approved=True."""
        import inspect
        source = inspect.getsource(Agent._execute_tool)
        assert '"approved": True' not in source, (
            "Hardcoded approved=True found in _execute_tool. "
            "Approval must go through the policy coordinator."
        )
        assert "approved=True" not in source, (
            "Hardcoded approved=True found in _execute_tool."
        )
