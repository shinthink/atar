"""F1: /retry and /undo tests."""

from __future__ import annotations

import os
import tempfile

import pytest
from atar_core.agent import Agent
from atar_core.checkpoint_manager import get_checkpoints, reset_checkpoints
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
    """Verify undo (filesystem restore) and retry behavior."""

    @pytest.mark.asyncio
    async def test_undo_empty_history_returns_empty(self) -> None:
        """Undo on empty history returns empty list, no crash."""
        reset_checkpoints()
        agent = Agent(provider=FakeSimpleProvider())
        result = agent.undo_last_turn()
        assert result == []

    @pytest.mark.asyncio
    async def test_undo_restores_file(self) -> None:
        """Undo restores file content to pre-checkpoint state."""
        reset_checkpoints()
        agent = Agent(provider=FakeSimpleProvider())
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write("original")
        tmp.close()

        # Save checkpoint
        get_checkpoints().save(1, "write_file", tmp.name)

        # Modify file
        with open(tmp.name, "w") as f:
            f.write("modified")

        # Undo should restore
        restored = agent.undo_last_turn()
        assert tmp.name in restored or any(tmp.name in r for r in restored)
        with open(tmp.name) as f:
            assert f.read() == "original"
        os.unlink(tmp.name)

    @pytest.mark.asyncio
    async def test_undo_new_file_deletes(self) -> None:
        """Undo deletes file that was newly created."""
        reset_checkpoints()
        agent = Agent(provider=FakeSimpleProvider())
        tmp = f"/tmp/_atar_undo_test_{os.getpid()}.txt"

        # Simulate creating a new file
        with open(tmp, "w") as f:
            f.write("new content")

        # Save checkpoint (file was new, get_checkpoints uses sentinel)
        # Manually simulate: agent wrote a new file, checkpoint was saved with empty content
        from atar_core.checkpoint_manager import Checkpoint
        import time
        cp = Checkpoint(turn=1, timestamp=time.time(), tool="write_file",
                       file_path=tmp, content="")
        get_checkpoints()._checkpoints.append(cp)

        restored = agent.undo_last_turn()
        assert "deleted" in str(restored).lower()
        assert not os.path.exists(tmp)  # file should be gone

    @pytest.mark.asyncio
    async def test_retry_returns_last_user_message(self) -> None:
        """Retry returns the last user message for in-place regenerate."""
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
