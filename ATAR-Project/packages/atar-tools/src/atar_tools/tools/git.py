"""ATAR git tool — safe read-only git operations (+ commit with approval)."""

from __future__ import annotations

from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _git(  # noqa: C901
    _name: str, args: dict[str, Any], ctx: ToolContext
) -> ToolResult:
    from atar_tools.registry import execute

    op = args.get("op", "status")
    cwd = args.get("cwd") or ctx.working_directory

    if op == "status":
        r = await execute("terminal", {"command": "git status --short", "cwd": cwd})
        return r

    if op == "diff":
        staged = "--staged" if args.get("staged") else ""
        r = await execute("terminal", {"command": f"git diff {staged}", "cwd": cwd})
        return r

    if op == "log":
        n = args.get("n", 10)
        r = await execute("terminal", {"command": f"git log --oneline -{n}", "cwd": cwd})
        return r

    if op == "branch":
        r = await execute("terminal", {"command": "git branch", "cwd": cwd})
        return r

    if op == "commit":
        msg = args.get("message", "")
        if not msg:
            return ToolResult(success=False, error="commit requires message")
        files = args.get("files", ".")
        r = await execute("terminal", {
            "command": f"git add {files} && git commit -m '{msg}'", "cwd": cwd
        })
        return r

    return ToolResult(success=False, error=f"Unknown git op: {op}")


register(
    "git",
    "Git operations: status, diff, log, branch, commit (destructive)",
    _git,
    parameters={
        "type": "object",
        "properties": {
            "op": {
                "type": "string",
                "enum": ["status", "diff", "log", "branch", "commit"],
                "description": "Git operation"
            },
            "cwd": {"type": "string", "description": "Working directory"},
            "message": {"type": "string", "description": "Commit message (for commit)"},
            "files": {"type": "string", "description": "Files to add (for commit)"},
            "staged": {"type": "boolean", "description": "Show staged diff"},
            "n": {"type": "integer", "description": "Number of log entries"},
        },
        "required": ["op"],
    },
    destructive=True,
    requires_approval=True,
)
