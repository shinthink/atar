"""ATAR agent budgets — iteration control and structured terminal states."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto


class TerminalState(Enum):
    """Why the agent stopped."""
    COMPLETED = auto()           # natural completion — model returned final text
    BLOCKED_NEEDS_USER = auto()  # approval required or user interaction needed
    FAILED = auto()              # unrecoverable error
    CANCELLED = auto()           # user cancelled via Ctrl+C
    BUDGET_EXHAUSTED = auto()    # max turns/tools/time/cost reached
    PROVIDER_EXHAUSTED = auto()  # all providers failed


@dataclass
class RunBudget:
    """Budgets that bound an agent run."""
    max_turns: int = 8
    max_tool_calls: int = 20
    max_time_seconds: float = 300
    max_repeated_calls: int = 5
    max_cost_cents: int | None = None

    turns_used: int = 0
    tools_used: int = 0
    started_at: float = field(default_factory=time.monotonic)
    cost_cents: int = 0
    repeated_map: dict[str, int] = field(default_factory=dict)

    def record_turn(self) -> None:
        self.turns_used += 1

    def record_tool(self, name: str) -> None:
        self.tools_used += 1
        self.repeated_map[name] = self.repeated_map.get(name, 0) + 1

    def turns_remaining(self) -> int:
        return max(0, self.max_turns - self.turns_used)

    def tools_remaining(self) -> int:
        return max(0, self.max_tool_calls - self.tools_used)

    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    def time_remaining(self) -> float:
        return max(0.0, self.max_time_seconds - self.elapsed())

    def is_exhausted(self) -> TerminalState | None:
        """Return the terminal state if any budget is exhausted, or None."""
        if self.turns_used >= self.max_turns:
            return TerminalState.BUDGET_EXHAUSTED
        if self.tools_used >= self.max_tool_calls:
            return TerminalState.BUDGET_EXHAUSTED
        if self.elapsed() >= self.max_time_seconds:
            return TerminalState.BUDGET_EXHAUSTED
        return None

    def too_many_repeated(self, tool_name: str) -> bool:
        return self.repeated_map.get(tool_name, 0) >= self.max_repeated_calls

    def snapshot(self) -> dict:
        return {
            "turns_used": self.turns_used,
            "tools_used": self.tools_used,
            "elapsed": round(self.elapsed(), 2),
            "repeated": dict(self.repeated_map),
        }


@dataclass
class RunResult:
    """Structured result from an agent run."""
    state: TerminalState
    final_text: str = ""
    evidence: list[dict] = field(default_factory=list)
    budget: dict = field(default_factory=dict)
    error: str | None = None
