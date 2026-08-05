"""ATAR delegation — spawn isolated subagents for parallel work."""

from __future__ import annotations

from typing import Any

from atar_core.agent import Agent
from atar_core.budgets import RunBudget, TerminalState
from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _delegate_task(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Spawn a subagent to accomplish a goal and return a summary."""
    goal = args.get("goal", "")
    if not goal:
        return ToolResult(success=False, error="goal required")

    sub_budget = RunBudget(
        max_turns=min(args.get("max_turns", 5), 10),
        max_tool_calls=min(args.get("max_tools", 10), 20),
        max_time_seconds=min(args.get("timeout", 120), 300),
    )

    try:
        # Create sub-agent with same provider, isolated messages
        provider = getattr(ctx, "provider", None) or _get_default_provider()
        if provider is None:
            return ToolResult(success=False, error="No provider available for delegation")
        sub = Agent(
            provider=provider,
            max_turns=sub_budget.max_turns,
            tools=None,
            system_prompt=f"You are an ATAR subagent. Complete this task concisely:\n{goal}\n\nReturn only the result. Be brief.",
            session_id=f"sub_{hash(goal) & 0xFFFF:04x}",
        )

        result = await sub.run(goal, budget=sub_budget)

        return ToolResult(
            success=result.state == TerminalState.COMPLETED,
            output=result.final_text or "(no output)",
            error=result.error,
            metadata={
                "sub_state": result.state.name,
                "budget": result.budget,
                "delegated": True,
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=f"Delegation failed: {e}", metadata={"delegated": True})


def _get_default_provider():
    """Get the default provider client (ModelProvider, not ProviderProfile)."""
    from atar_core.provider_router import create_router
    try:
        router = create_router()
        if router.providers:
            return router  # Router itself acts as ModelProvider for Agent
    except Exception:
        pass
    return None


def _get_sub_provider(profile):
    """Create a ModelProvider from a ProviderProfile."""
    from atar_core.provider_router import _build_provider
    try:
        return _build_provider(profile)
    except Exception:
        return None


register(
    "delegate_task",
    "Spawn a subagent to accomplish a goal independently",
    _delegate_task,
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Task for the subagent to accomplish"},
            "max_turns": {"type": "integer", "description": "Max turns (default 5, max 10)"},
            "max_tools": {"type": "integer", "description": "Max tool calls (default 10)"},
            "timeout": {"type": "integer", "description": "Max seconds (default 120)"},
        },
        "required": ["goal"],
    },
)
