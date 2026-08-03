"""Skill tools — load_skill for on-demand skill content retrieval."""

from __future__ import annotations

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _load_skill(name: str, args: dict, ctx: ToolContext) -> ToolResult:
    skill_name = args.get("name", "")
    if not skill_name:
        return ToolResult(success=False, error="Missing skill name")
    from atar_core.skills import get_skill_manager
    mgr = get_skill_manager()
    content = mgr.load_skill_md(skill_name)
    if content is None:
        return ToolResult(success=False, error=f"Skill '{skill_name}' not found")
    return ToolResult(success=True, output=content[:5000])

register("load_skill", "Load a skill's full SKILL.md content by name", _load_skill, parameters={
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Skill name to load"},
    },
    "required": ["name"],
}, destructive=False)
