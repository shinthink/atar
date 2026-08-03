"""ATAR tool registry — thread-safe, self-registering tools per blueprint Section 11."""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from atar_models.tools import ToolContext, ToolResult

Handler = Callable[[str, dict[str, Any], ToolContext], Coroutine[Any, Any, ToolResult]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    handler: Handler | None = None
    max_output_chars: int = 50_000
    destructive: bool = False
    requires_approval: bool = False


_registry: dict[str, Tool] = {}
_toolsets: dict[str, list[str]] = {}


def register(
    name: str,
    description: str,
    handler: Handler,
    *,
    parameters: dict[str, Any] | None = None,
    max_output_chars: int = 50_000,
    destructive: bool = False,
    requires_approval: bool = False,
    toolset: str = "builtin",
) -> Tool:
    tool = Tool(
        name=name,
        description=description,
        parameters=parameters or {},
        handler=handler,
        max_output_chars=max_output_chars,
        destructive=destructive,
        requires_approval=requires_approval,
    )
    _registry[name] = tool
    _toolsets.setdefault(toolset, []).append(name)
    return tool


def get(name: str) -> Tool | None:
    return _registry.get(name)


def list_all() -> list[Tool]:
    return sorted(_registry.values(), key=lambda t: t.name)


def list_toolset(name: str) -> list[Tool]:
    return [t for t in list_all() if t.name in _toolsets.get(name, [])]


async def execute(name: str, args: dict[str, Any], ctx: ToolContext | None = None) -> ToolResult:
    ctx = ctx or ToolContext()
    tool = _registry.get(name)
    if not tool:
        return ToolResult(success=False, error=f"Tool '{name}' not found")
    if not tool.handler:
        return ToolResult(success=False, error=f"Tool '{name}' has no handler")
    # Approval check
    if tool.requires_approval and not ctx.metadata.get("approved"):
        return ToolResult(
            success=False,
            error=f"Tool '{name}' requires approval. Set approved=true in context.",
            evidence={"requires_approval": True, "tool": name},
        )
    # Audit
    from atar_security.audit import log_action
    cid = ctx.metadata.get("correlation_id", "")
    log_action(f"tool:{name}", args=str(args)[:200], correlation_id=cid)
    try:
        result = await tool.handler(name, args, ctx)
        if len(result.output) > tool.max_output_chars:
            result.output = result.output[:tool.max_output_chars] + "\n... [truncated]"
        return result
    except Exception as exc:
        return ToolResult(success=False, error=str(exc))


def to_schema(tool: Tool) -> dict[str, Any]:
    """Provider-agnostic tool schema. Providers adapt independently."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters or {"type": "object", "properties": {}},
    }


def to_openai_schema(tool: Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters or {"type": "object", "properties": {}},
        },
    }


def to_anthropic_schema(tool: Tool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.parameters or {"type": "object", "properties": {}},
    }



# Auto-import all tool modules for registration
def _import_all_tools() -> None:
    try: import atar_tools.tools.file  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.terminal  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.web  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.web_search  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.git  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.session  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.delegation  # noqa: F401
    except ImportError: pass
    try: import atar_tools.tools.test_runner  # noqa: F401
    except ImportError: pass

_import_all_tools()
