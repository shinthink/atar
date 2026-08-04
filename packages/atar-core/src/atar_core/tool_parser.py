"""ATAR tool call parser — extracts and executes tools from model text output.

Per F-009: Structured tool parsing from provider text responses.
"""

from __future__ import annotations

import re
from typing import Any

from atar_models.tools import ToolContext, ToolResult


def extract_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse tool calls from model text. Supports code blocks and inline commands."""
    calls = []

    # Pattern 1: ```bash ... ``` blocks
    for match in re.finditer(r"```(?:bash|shell|sh)\n(.*?)```", text, re.DOTALL):
        cmd = match.group(1).strip()
        if cmd:
            calls.append({"tool": "terminal", "args": {"command": cmd}})

    # Pattern 2: `command` backtick inline
    for match in re.finditer(r"`([a-zA-Z][a-zA-Z0-9_\-./ ]{2,})`", text):
        cmd = match.group(1).strip()
        if any(kw in cmd.lower() for kw in ("git ", "pytest", "find ", "grep ", "cat ", "ls ", "echo ", "pip ")):
            calls.append({"tool": "terminal", "args": {"command": cmd}})

    return calls


async def execute_extracted(text: str, ctx: ToolContext | None = None) -> list[ToolResult]:
    """Extract and execute tool calls from model response text."""
    from atar_tools.registry import execute as tool_execute
    calls = extract_tool_calls(text)
    results = []
    for call in calls:
        result = await tool_execute(call["tool"], call["args"], ctx)
        results.append(result)
    return results
