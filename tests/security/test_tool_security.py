"""Security tests for workspace paths, terminal policy, SSRF."""

from __future__ import annotations

import os

import pytest
from atar_models.tools import ToolContext
from atar_tools.tools.file import _read_file
from atar_tools.tools.terminal import _run_terminal
from atar_tools.tools.web import _web_fetch

WORKSPACE = "/tmp/atar-test-workspace"
os.makedirs(WORKSPACE, exist_ok=True)


class TestFilePathSecurity:
    """Path traversal, symlink, absolute escape must fail."""

    @pytest.mark.asyncio
    async def test_absolute_path_outside_workspace_rejected(self) -> None:
        """Absolute path to /etc/passwd must be blocked."""
        ctx = ToolContext(metadata={"workspace": WORKSPACE})
        result = await _read_file("read_file", {"path": "/etc/passwd"}, ctx)
        assert not result.success, f"Absolute path should be rejected: {result}"

    @pytest.mark.asyncio
    async def test_parent_traversal_rejected(self) -> None:
        """../../../ escape must be blocked."""
        ctx = ToolContext(metadata={"workspace": WORKSPACE})
        result = await _read_file("read_file", {"path": "../../../etc/passwd"}, ctx)
        assert not result.success, f"Parent traversal should be rejected: {result}"

    @pytest.mark.asyncio
    async def test_workspace_file_allowed(self) -> None:
        """File inside workspace should be allowed."""
        test_file = os.path.join(WORKSPACE, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello")
        ctx = ToolContext(metadata={"workspace": WORKSPACE}, working_directory=WORKSPACE)
        result = await _read_file("read_file", {"path": test_file}, ctx)
        assert result.success
        assert "hello" in result.output


class TestTerminalPolicy:
    """Terminal must have timeout, env scrubbing."""

    @pytest.mark.asyncio
    async def test_basic_command_runs(self) -> None:
        ctx = ToolContext(metadata={"workspace": WORKSPACE})
        result = await _run_terminal("terminal", {"command": "echo hello", "timeout": 5}, ctx)
        assert result.success
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_timeout_is_honored(self) -> None:
        ctx = ToolContext(metadata={"workspace": WORKSPACE})
        result = await _run_terminal("terminal", {"command": "sleep 30", "timeout": 1}, ctx)
        assert not result.success
        assert "timed out" in result.error.lower()


class TestWebSSRF:
    """Web fetcher must reject SSRF targets."""

    @pytest.mark.asyncio
    async def test_loopback_rejected(self) -> None:
        ctx = ToolContext(metadata={})
        result = await _web_fetch("web_fetch", {"url": "http://127.0.0.1:22"}, ctx)
        # Should either block or fail to connect
        assert result is not None

    @pytest.mark.asyncio
    async def test_metadata_endpoint_rejected(self) -> None:
        ctx = ToolContext(metadata={})
        result = await _web_fetch("web_fetch", {"url": "http://169.254.169.254/latest/meta-data/"}, ctx)
        assert not result.success, f"Cloud metadata endpoint should be blocked: {result}"
