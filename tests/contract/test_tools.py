"""Contract tests for ATAR tools — with approval context."""

from __future__ import annotations

import os
import tempfile

import atar_tools.tools.file as _file  # noqa: F401
import atar_tools.tools.terminal as _terminal  # noqa: F401
import pytest
from atar_models.tools import ToolContext
from atar_tools.registry import execute, get, list_all

APPROVED = ToolContext(metadata={"approved": True})


@pytest.mark.asyncio
async def test_read_file_tool() -> None:
    ctx = ToolContext(metadata={}, working_directory=tempfile.gettempdir())
    path = os.path.join(tempfile.gettempdir(), "atar_test_read.txt")
    with open(path, "w") as f:
        f.write("test content")
    try:
        result = await execute("read_file", {"path": "atar_test_read.txt"}, ctx)
        assert result.success
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_write_file_tool() -> None:
    ctx = ToolContext(metadata={"approved": True}, working_directory=tempfile.gettempdir())
    path = os.path.join(tempfile.gettempdir(), "atar_test_write.txt")
    try:
        result = await execute("write_file", {"path": "atar_test_write.txt", "content": "test"}, ctx)
        assert result.success
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.asyncio
async def test_terminal_tool() -> None:
    result = await execute("terminal", {"command": "echo hello"}, APPROVED)
    assert result.success
    assert "hello" in result.output


@pytest.mark.asyncio
async def test_terminal_tool_failure() -> None:
    result = await execute("terminal", {"command": "exit 1"}, APPROVED)
    assert not result.success


@pytest.mark.asyncio
async def test_terminal_timeout() -> None:
    result = await execute("terminal", {"command": "sleep 5", "timeout": 1}, APPROVED)
    assert "Timed out" in result.error


@pytest.mark.asyncio
async def test_unknown_tool() -> None:
    result = await execute("nonexistent", {})
    assert not result.success
    assert "not found" in result.error


def test_list_all() -> None:
    tools = list_all()
    names = [t.name for t in tools]
    assert "read_file" in names
    assert "write_file" in names
    assert "terminal" in names


def test_get_tool() -> None:
    t = get("read_file")
    assert t is not None
    assert t.name == "read_file"


def test_write_file_blocked_without_approval() -> None:
    import asyncio
    result = asyncio.run(execute("write_file", {"path": "/tmp/nope.txt", "content": "x"}))
    assert not result.success
    assert "requires approval" in result.error
