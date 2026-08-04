"""ATAR toolsets — composable tool groups with enable/disable."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atar_tools.registry import list_all

# Tool-to-toolset mapping
_TOOL_TOOLSETS: dict[str, str] = {
    "read_file": "file",
    "write_file": "file",
    "patch": "file",
    "search_files": "file",
    "terminal": "terminal",
    "run_tests": "terminal",
    "git": "terminal",
    "web_search": "web",
    "web_fetch": "web",
    "browser": "browser",
    "session_search": "sessions",
    "session_resume": "sessions",
    "execute_code": "code_execution",
    "cronjob": "scheduler",
    "delegate_task": "delegation",
}

# Toolset definitions with defaults
DEFAULT_TOOLSETS: dict[str, dict[str, Any]] = {
    "safe": {"enabled": True, "description": "Read-only safe tools"},
    "file": {"enabled": True, "description": "File read/write/patch"},
    "terminal": {"enabled": True, "description": "Shell commands and git"},
    "web": {"enabled": True, "description": "Web search and fetch"},
    "browser": {"enabled": False, "description": "Headless browser"},
    "sessions": {"enabled": True, "description": "Session search and resume"},
    "code_execution": {"enabled": False, "description": "Python code execution"},
    "scheduler": {"enabled": False, "description": "Cron job scheduling"},
    "delegation": {"enabled": False, "description": "Subagent delegation"},
}


@dataclass
class Toolset:
    name: str
    description: str = ""
    enabled: bool = True
    tools: list[Any] = field(default_factory=list)


def get_toolsets(enabled_only: bool = True) -> dict[str, Toolset]:
    """Get all toolsets with their tools."""
    all_tools = list_all()
    result: dict[str, Toolset] = {}

    for ts_name, ts_cfg in DEFAULT_TOOLSETS.items():
        if enabled_only and not ts_cfg.get("enabled", True):
            continue
        tools = [t for t in all_tools if _TOOL_TOOLSETS.get(t.name, "") == ts_name]
        # "safe" toolset: all read-only tools from any toolset
        if ts_name == "safe":
            safe_names = {"read_file", "search_files", "session_search", "session_resume"}
            tools = [t for t in all_tools if t.name in safe_names]
        result[ts_name] = Toolset(
            name=ts_name,
            description=ts_cfg.get("description", ""),
            enabled=ts_cfg.get("enabled", True),
            tools=tools,
        )

    return result


def tools_for_toolsets(toolset_names: list[str]) -> list[Any]:
    """Get all tools belonging to the specified toolsets."""
    all_tools = list_all()
    result = []
    seen = set()

    for ts_name in toolset_names:
        for t in all_tools:
            toolset = _TOOL_TOOLSETS.get(t.name, "")
            if toolset == ts_name and t.name not in seen:
                result.append(t)
                seen.add(t.name)
            # "safe" includes read-only from any toolset
            if ts_name == "safe" and t.name in {"read_file", "search_files", "session_search", "session_resume"} and t.name not in seen:
                result.append(t)
                seen.add(t.name)

    return result


def enabled_toolsets() -> list[str]:
    """List names of currently enabled toolsets."""
    return [name for name, cfg in DEFAULT_TOOLSETS.items() if cfg.get("enabled", True)]


_active_toolset: str = ""


def set_active_toolset(name: str) -> None:
    global _active_toolset
    _active_toolset = name


def get_active_toolset() -> str:
    return _active_toolset


def get_active_toolset_names() -> set[str]:
    if not _active_toolset:
        return set()
    return {_active_toolset}
