"""Contract tests for ATAR tools."""

from __future__ import annotations

import os
import tempfile

# Trigger self-registration at module load
import atar_tools.tools.file as _file  # noqa: F401
import atar_tools.tools.terminal as _terminal  # noqa: F401
import pytest
from atar_tools.registry import execute, get, list_all


@pytest.mark.asyncio
async def test_read_file_tool() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello world")
        path = f.name
    try:
        result = await execute("read_file", {"path": path})
        assert result.success
        assert "hello world" in result.output
    finally:
        os.unlink(path)


@pytest.mark.asyncio
async def test_write_file_tool() -> None:
    path = os.path.join(tempfile.gettempdir(), "atar_test_write.txt")
    try:
        result = await execute("write_file", {"path": path, "content": "test"})
        assert result.success
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "test"
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_terminal_tool() -> None:
    result = await execute("terminal", {"command": "echo hello"})
    assert result.success
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_terminal_tool_failure() -> None:
    result = await execute("terminal", {"command": "exit 1"})
    assert not result.success
    assert result.metadata.get("exit_code") == 1


@pytest.mark.asyncio
async def test_terminal_timeout() -> None:
    result = await execute("terminal", {"command": "sleep 5", "timeout": 1})
    assert not result.success
    assert "Timed out" in result.error


@pytest.mark.asyncio
async def test_unknown_tool() -> None:
    result = await execute("nonexistent", {})
    assert not result.success
    assert "not found" in result.error


def test_list_all() -> None:
    tools = list_all()
    names = {t.name for t in tools}
    assert "read_file" in names
    assert "write_file" in names
    assert "terminal" in names


def test_write_file_is_destructive() -> None:
    tool = get("write_file")
    assert tool is not None
    assert tool.destructive is True
    assert tool.requires_approval is True
