"""Granular per-session approval gates for tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ApprovalState:
    """Per-session approval tracking."""
    yolo: bool = False
    # tool_name -> "ask" | "always" | "never"
    tool_modes: dict[str, str] = field(default_factory=dict)
    # file_path -> True (always approve writes to this file)
    file_always: set[str] = field(default_factory=set)

    def resolve(self, tool_name: str, file_path: str = "") -> str:
        """Resolve approval action for a tool call."""
        if self.yolo:
            return "approve"
        if file_path and file_path in self.file_always:
            return "approve"
        mode = self.tool_modes.get(tool_name, "ask")
        if mode == "always":
            return "approve"
        if mode == "never":
            return "reject"
        return "ask"

    def set_tool_mode(self, tool_name: str, mode: str) -> None:
        self.tool_modes[tool_name] = mode

    def add_file_always(self, file_path: str) -> None:
        self.file_always.add(file_path)


# Global per-session instance — reset each REPL launch
_approval_state: ApprovalState | None = None


def get_approval() -> ApprovalState:
    global _approval_state
    if _approval_state is None:
        _approval_state = ApprovalState()
    return _approval_state


def reset_approval() -> None:
    global _approval_state
    _approval_state = ApprovalState()


def format_approval_prompt(tool_name: str, file_path: str, diff_markup: str, stats: dict) -> str:
    """Build the Rich-formatted approval prompt with 5 choices."""
    from atar_tools.tools.diff_renderer import diff_stats_line
    return f"""[bold]Approve {tool_name} to {file_path}?[/] {diff_stats_line(stats)}

{diff_markup}

[bold]Choices:[/]
  [1] Yes, apply this change
  [2] Yes, and don't ask again for this file this session
  [3] Yes, and don't ask again for this tool this session
  [4] No, reject and tell agent what to change
  [5] No, and stop the task"""
