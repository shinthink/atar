"""ATAR output truncation — limit tool result size entering model context."""

from __future__ import annotations

# Default max chars per tool type
TOOL_MAX_CHARS: dict[str, int] = {
    "web_fetch": 3000,
    "terminal": 2000,
    "read_file": 5000,
    "web_search": 4000,
    "session_search": 3000,
    "_default": 2000,
}

# Store full outputs for /tools output <n>
_full_outputs: dict[int, str] = {}


def truncate_tool_output(output: str, tool_name: str = "", max_chars: int | None = None) -> str:
    """Truncate tool output with head + tail strategy. Full output saved separately."""
    limit = max_chars or TOOL_MAX_CHARS.get(tool_name, TOOL_MAX_CHARS["_default"])
    if len(output) <= limit:
        return output

    head_size = int(limit * 0.7)
    tail_size = limit - head_size - 100  # reserve for message
    truncated = (
        output[:head_size]
        + f"\n\n... [{len(output) - head_size - tail_size} chars hidden, use /tools output to see full] ...\n\n"
        + output[-tail_size:]
    )
    return truncated


def save_full_output(turn: int, output: str) -> None:
    _full_outputs[turn] = output


def get_full_output(turn: int) -> str | None:
    return _full_outputs.get(turn)
