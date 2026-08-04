"""ATAR terminal tool — hardened subprocess execution with process-tree kill."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import signal
from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register

# Safe minimal environment — no host secrets forwarded
_SAFE_ENV: dict[str, str] = {
    "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
    "HOME": os.environ.get("HOME", os.path.expanduser("~")),
    "LANG": os.environ.get("LANG", "C.UTF-8"),
    "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
}

# Dangerous patterns blocked for safety
_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r";\s*\w", "command chaining with ;"),
    (r"&&\s*\w", "command chaining with &&"),
    (r"\|\|\s*\w", "command chaining with ||"),
    (r"\$\(", "command substitution $()"),
    (r"`[^`]+`", "command substitution with backticks"),
    (r">\s*/dev/", "redirect to system device"),
    (r">\s*/etc/", "write to /etc/"),
    (r">\s*/proc/", "write to /proc/"),
    (r"rm\s+-rf\s+/", "recursive root deletion"),
    (r"mkfs\.", "filesystem format"),
    (r"dd\s+if=", "raw disk access"),
    (r"chmod\s+777\s+/", "world-writable system path"),
    (r"curl.*\|.*sh", "curl pipe to shell"),
    (r"wget.*\|.*sh", "wget pipe to shell"),
]


def _validate_command(command: str) -> str | None:
    """Validate a shell command for dangerous patterns. Returns error message or None if safe."""
    for pattern, description in _DANGEROUS_PATTERNS:
        if re.search(pattern, command):
            return f"Blocked dangerous pattern: {description}"
    return None


async def _run_terminal(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    command = args.get("command", "")
    if not command:
        return ToolResult(success=False, error="command required")

    # Security: validate command before execution
    err = _validate_command(command)
    if err:
        return ToolResult(success=False, error=err)

    cwd = args.get("cwd") or ctx.working_directory or os.getcwd()
    timeout = min(args.get("timeout", 30), 300)  # max 5 minutes
    max_output = 20_000

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=_SAFE_ENV,
            start_new_session=True,  # create new process group for tree-kill
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            _kill_process_tree(proc.pid)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            except TimeoutError:
                return ToolResult(success=False, error=f"Timed out after {timeout}s (process would not die)")

            output = stdout.decode("utf-8", errors="replace")[:max_output]
            if len(stdout) > max_output:
                output += f"\n[truncated: {len(stdout)} bytes]"
            return ToolResult(
                success=False,
                output=output,
                error=f"Timed out after {timeout}s — process killed",
                metadata={"exit_code": proc.returncode or -9, "cwd": cwd, "timed_out": True},
            )

        output = stdout.decode("utf-8", errors="replace")[:max_output]
        err = stderr.decode("utf-8", errors="replace")[:max_output]

        if len(stdout) > max_output or len(stderr) > max_output:
            output += "\n[output truncated]"

        return ToolResult(
            success=proc.returncode == 0,
            output=output + (f"\n[stderr]\n{err}" if err else ""),
            metadata={"exit_code": proc.returncode, "cwd": cwd},
        )

    except FileNotFoundError:
        return ToolResult(success=False, error=f"Command not found. Use full path or install: {command.split()[0]}")
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {command.split()[0]}")


def _kill_process_tree(pid: int) -> None:
    """Kill the entire process group."""
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)


register("terminal", "Run a shell command", _run_terminal, parameters={
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "Command to run"},
        "cwd": {"type": "string", "description": "Working directory"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (max 300)"},
    },
    "required": ["command"],
}, destructive=True, requires_approval=True, max_output_chars=20_000)
