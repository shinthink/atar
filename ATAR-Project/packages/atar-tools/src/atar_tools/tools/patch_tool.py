"""ATAR patch tool — diff-generation with Rich syntax highlighting."""

from __future__ import annotations

import difflib
import os

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _patch_file(name: str, args: dict, ctx: ToolContext) -> ToolResult:
    path = args.get("path", "")
    old_string = args.get("old_string", "")
    new_string = args.get("new_string", "")
    replace_all = args.get("replace_all", False)

    if not path or not old_string:
        return ToolResult(success=False, error="patch requires path, old_string, new_string")

    # Safety: resolve path within workspace
    real = os.path.realpath(path)
    cwd = os.path.realpath(os.getcwd())
    if not real.startswith(cwd):
        return ToolResult(success=False, error=f"Path outside workspace: {path}")

    if not os.path.exists(real):
        # New file
        os.makedirs(os.path.dirname(real) or ".", exist_ok=True)
        with open(real, "w") as f:
            f.write(new_string)
        return ToolResult(success=True, output=f"Created {path} ({len(new_string)} bytes)")

    with open(real) as f:
        old_lines = f.readlines()

    new_content = "".join(old_lines)
    if replace_all:
        new_content = new_content.replace(old_string, new_string)
    else:
        if old_string not in new_content:
            return ToolResult(success=False, error="old_string not found in file")
        new_content = new_content.replace(old_string, new_string, 1)

    from atar_tools.tools.checkpoints import checkpoint_before_write
    checkpoint_before_write(safe)
    # Generate unified diff
    old_stripped = [line.rstrip("\n") for line in old_lines]
    new_stripped = [line.rstrip("\n") for line in new_content.splitlines(keepends=True)]
    diff_lines = list(difflib.unified_diff(
        old_stripped, new_stripped,
        fromfile=f"a/{path}", tofile=f"b/{path}",
    ))

    # Apply the change
    with open(real, "w") as f:
        f.write(new_content)

    diff_output = "\n".join(diff_lines)
    return ToolResult(success=True, output=diff_output)


register("patch", "Apply a find-and-replace edit to a file, with diff preview",
    _patch_file, parameters={
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "File path to patch"},
        "old_string": {"type": "string", "description": "Text to find and replace"},
        "new_string": {"type": "string", "description": "Replacement text"},
        "replace_all": {"type": "boolean", "description": "Replace all occurrences (default: false)"},
    },
    "required": ["path", "old_string", "new_string"],
}, destructive=True, requires_approval=True)
