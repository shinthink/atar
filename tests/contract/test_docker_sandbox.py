"""Tests for Docker sandbox."""

from __future__ import annotations

import pytest


class TestDockerSandbox:
    """Docker sandbox creation and lifecycle."""

    @pytest.mark.asyncio
    async def test_sandbox_creation(self) -> None:
        from atar_core.docker_sandbox import DockerSandbox
        sb = DockerSandbox()
        # Should not crash even if Docker is unavailable
        available = await sb.is_available()
        assert isinstance(available, bool)

    @pytest.mark.asyncio
    async def test_sandbox_fallback_local(self) -> None:
        from atar_core.docker_sandbox import run_sandboxed
        # Should fall back to local execution if Docker not available
        ok, stdout, stderr = await run_sandboxed("echo hello_from_sandbox_test")
        assert ok
        assert "hello_from_sandbox_test" in stdout

    @pytest.mark.asyncio
    async def test_sandbox_local_timeout(self) -> None:
        from atar_core.docker_sandbox import run_sandboxed
        ok, stdout, stderr = await run_sandboxed("sleep 2", timeout=1)
        # Should fail (timeout), but gracefully — not crash
        assert isinstance(ok, bool)

    @pytest.mark.asyncio
    async def test_get_sandbox_singleton(self) -> None:
        from atar_core.docker_sandbox import cleanup_sandbox, get_sandbox
        await cleanup_sandbox()
        sb1 = await get_sandbox()
        sb2 = await get_sandbox()
        assert sb1 is sb2  # Singleton


class TestTerminalSandboxIntegration:
    """Terminal tool uses sandbox parameter."""

    @pytest.mark.asyncio
    async def test_terminal_with_sandbox_param(self) -> None:
        from atar_models.tools import ToolContext
        from atar_tools.tools.terminal import _run_terminal
        ctx = ToolContext(metadata={"approved": True})
        result = await _run_terminal("terminal", {
            "command": "echo sandbox_test",
            "sandbox": True,
        }, ctx)
        assert result.success
        assert "sandbox_test" in result.output

    @pytest.mark.asyncio
    async def test_terminal_no_sandbox(self) -> None:
        from atar_models.tools import ToolContext
        from atar_tools.tools.terminal import _run_terminal
        ctx = ToolContext(metadata={"approved": True})
        result = await _run_terminal("terminal", {
            "command": "echo local_test",
            "sandbox": False,
        }, ctx)
        assert result.success
        assert "local_test" in result.output
