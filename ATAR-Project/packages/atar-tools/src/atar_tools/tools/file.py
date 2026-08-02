"""ATAR file tools — safe file read/write operations."""

from __future__ import annotations

import os
from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _read_file(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    if not path:
        return ToolResult(success=False, error="path required")
    full = os.path.join(ctx.working_directory, path) if not os.path.isabs(path) else path
    if not os.path.isfile(full):
        return ToolResult(success=False, error=f"Not found: {full}")
    try:
        with open(full, errors="replace") as f:
            content = f.read()
        return ToolResult(
            success=True, output=content, metadata={"path": full, "bytes": len(content)}
        )
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {full}")


async def _write_file(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return ToolResult(success=False, error="path required")
    full = os.path.join(ctx.working_directory, path) if not os.path.isabs(path) else path
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    try:
        with open(full, "w") as f:
            f.write(content)
        return ToolResult(
            success=True,
            output=f"Wrote {len(content)} bytes to {full}",
            metadata={"path": full},
        )
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {full}")


register("read_file", "Read a file from disk", _read_file, parameters={
    "type": "object",
    "properties": {"path": {"type": "string", "description": "File path"}},
    "required": ["path"],
})

register("write_file", "Write content to a file", _write_file, parameters={
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "File path"},
        "content": {"type": "string", "description": "Content to write"},
    },
    "required": ["path", "content"],
}, destructive=True, requires_approval=True)
