"""ATAR file tools — safe file read/write operations with path hardening."""

from __future__ import annotations

import os
from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


def _resolve_safe_path(path: str, ctx: ToolContext, must_exist: bool = False) -> tuple[str | None, str | None]:
    """Resolve path within workspace. Returns (safe_abs_path, error) or (None, error)."""
    workspace = os.path.abspath(ctx.working_directory or os.getcwd())

    candidate = os.path.abspath(path) if os.path.isabs(path) else os.path.abspath(os.path.join(workspace, path))

    try:
        real = os.path.realpath(candidate)
    except OSError:
        return None, f"Path resolution failed: {candidate}"

    if not real.startswith(workspace + os.sep) and real != workspace:
        return None, f"Path outside workspace: {path}"

    if ".." in os.path.relpath(real, workspace).split(os.sep):
        return None, f"Path traversal detected: {path}"

    if must_exist and not os.path.exists(real):
        return None, f"Not found: {real}"

    return real, None


async def _read_file(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    if not path:
        return ToolResult(success=False, error="path required")

    safe, err = _resolve_safe_path(path, ctx, must_exist=True)
    if err:
        return ToolResult(success=False, error=err)

    try:
        with open(safe, errors="replace") as f:
            content = f.read()
        # Truncate large files to prevent OOM
        max_chars = 100_000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... [truncated: {len(content)} bytes, showing first {max_chars}]"
        return ToolResult(
            success=True, output=content, metadata={"path": safe, "bytes": len(content)}
        )
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {safe}")


async def _write_file(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return ToolResult(success=False, error="path required")

    safe, err = _resolve_safe_path(path, ctx)
    if err:
        return ToolResult(success=False, error=err)

    os.makedirs(os.path.dirname(safe) or ".", exist_ok=True)
    try:
        from atar_tools.tools.checkpoints import checkpoint_before_write
        checkpoint_before_write(safe)
        with open(safe, "w") as f:
            f.write(content)
        return ToolResult(
            success=True,
            output=f"Wrote {len(content)} bytes to {safe}",
            metadata={"path": safe},
        )
    except PermissionError:
        return ToolResult(success=False, error=f"Permission denied: {safe}")


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
