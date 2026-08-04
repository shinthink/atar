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
        # Track failed skill load for self-improvement
        try:
            from atar_core.skill_improvement import record_skill_use
            record_skill_use(skill_name, success=False, error=f"Skill '{skill_name}' not found")
        except Exception:
            pass
        return ToolResult(success=False, error=f"Skill '{skill_name}' not found")

    # Track successful skill load
    try:
        from atar_core.skill_improvement import record_skill_use
        record_skill_use(skill_name, success=True)
    except Exception:
        pass

    return ToolResult(success=True, output=content[:5000])

register("load_skill", "Load a skill's full SKILL.md content by name", _load_skill, parameters={
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Skill name to load"},
    },
    "required": ["name"],
}, destructive=False)
