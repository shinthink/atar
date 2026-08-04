"""F1: /retry and /undo tests (disk-based)."""

from __future__ import annotations

import os
import tempfile

import pytest
from atar_core.agent import Agent
from atar_tools.tools.checkpoints import (
    checkpoint_before_write, clear_checkpoints,
    list_checkpoints, restore_checkpoint,
)
from atar_models.requests import Message


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
    def setup_method(self):
        clear_checkpoints()

    def test_undo_empty_returns_empty(self):
        agent = Agent(provider=FakeSimpleProvider())
        result = agent.undo_last_turn()
        assert result == []

    def test_undo_restores_file(self):
        agent = Agent(provider=FakeSimpleProvider())
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write("original")
        tmp.close()

        checkpoint_before_write(tmp.name)
        with open(tmp.name, "w") as f:
            f.write("modified")

        restored = agent.undo_last_turn()
        with open(tmp.name) as f:
            assert f.read() == "original"
        os.unlink(tmp.name)

    def test_multiple_checkpoints(self):
        tmp1 = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp1.write("v1")
        tmp1.close()
        tmp2 = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp2.write("v1")
        tmp2.close()

        checkpoint_before_write(tmp1.name)
        checkpoint_before_write(tmp2.name)
        with open(tmp1.name, "w") as f: f.write("v2")
        with open(tmp2.name, "w") as f: f.write("v2")

        agent = Agent(provider=FakeSimpleProvider())
        restored = agent.undo_last_turn(n=2)
        assert len(restored) >= 1
        os.unlink(tmp1.name)
        os.unlink(tmp2.name)

    def test_retry_returns_last_user_message(self):
        agent = Agent(provider=FakeSimpleProvider())
        agent._messages = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi there"),
        ]
        last = agent.retry_last_turn()
        assert last == "hello"

    def test_retry_empty_history(self):
        agent = Agent(provider=FakeSimpleProvider())
        assert agent.retry_last_turn() is None
