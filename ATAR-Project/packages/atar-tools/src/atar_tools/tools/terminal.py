"""ATAR terminal tool — async subprocess execution."""

from __future__ import annotations

import asyncio
from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _run_terminal(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    command = args.get("command", "")
    if not command:
        return ToolResult(success=False, error="command required")
    cwd = args.get("cwd") or ctx.working_directory
    timeout = args.get("timeout", 30)
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        output = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")
        return ToolResult(
            success=proc.returncode == 0,
            output=output + (f"\n[stderr]\n{err}" if err else ""),
            metadata={"exit_code": proc.returncode, "cwd": cwd},
        )
    except TimeoutError:
        return ToolResult(success=False, error=f"Timed out after {timeout}s")


register("terminal", "Run a shell command", _run_terminal, parameters={
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "Command to run"},
        "cwd": {"type": "string", "description": "Working directory"},
        "timeout": {"type": "integer", "description": "Timeout in seconds"},
    },
    "required": ["command"],
}, destructive=True, requires_approval=True, max_output_chars=20_000)
