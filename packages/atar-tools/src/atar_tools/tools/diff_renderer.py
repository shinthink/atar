"""ATAR diff renderer — Rich Syntax unified diff with stats."""

from __future__ import annotations

import difflib


def render_diff(
    old_content: str | None,
    new_content: str,
    file_path: str,
    old_label: str = "a",
    new_label: str = "b",
) -> tuple[str, str, dict]:
    """Generate a unified diff. Returns (markup, plain_text, stats)."""
    old_lines = (old_content or "").splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"{old_label}/{file_path}",
        tofile=f"{new_label}/{file_path}",
    ))

    added = sum(1 for ln in diff_lines if ln.startswith("+") and not ln.startswith("+++"))
    removed = sum(1 for ln in diff_lines if ln.startswith("-") and not ln.startswith("---"))
    stats = {"added": added, "removed": removed, "total_lines": len(diff_lines)}

    plain_text = "".join(diff_lines)

    # Rich markup: colorize +/- lines
    rich_lines = []
    for ln in diff_lines:
        if ln.startswith("+++") or ln.startswith("---"):
            rich_lines.append(f"[bold]{ln.rstrip()}[/]")
        elif ln.startswith("@@"):
            rich_lines.append(f"[bold #67D8FF]{ln.rstrip()}[/]")
        elif ln.startswith("+"):
            rich_lines.append(f"[#4ADE80]{ln.rstrip()}[/]")
        elif ln.startswith("-"):
            rich_lines.append(f"[#F87171]{ln.rstrip()}[/]")
        else:
            rich_lines.append(f"[dim]{ln.rstrip()}[/]")

    markup = "\n".join(rich_lines)
    return markup, plain_text, stats


def diff_stats_line(stats: dict) -> str:
    """Compact stats line: +12 -4."""
    return f"[#4ADE80]+{stats['added']}[/] [#F87171]-{stats['removed']}[/]"
