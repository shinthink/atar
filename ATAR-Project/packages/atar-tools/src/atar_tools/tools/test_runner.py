"""ATAR test runner — run pytest and return results."""

from __future__ import annotations

from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import execute, register


async def _run_tests(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    cwd = args.get("cwd") or ctx.working_directory
    path = args.get("path", "tests/")
    r = await execute("terminal", {"command": f"pytest {path} -q --tb=short", "cwd": cwd, "timeout": 120})
    return r


register(
    "run_tests",
    "Run pytest test suite",
    _run_tests,
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Test path (default: tests/)"},
            "cwd": {"type": "string", "description": "Working directory"},
        },
    },
    max_output_chars=30_000,
)
