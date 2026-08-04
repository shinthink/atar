"""ATAR memory nudge — proactive review prompts for memory maintenance.

Hermes-style periodic nudges to review, update, and prune memories.
Tracks last review time and memory count to determine when to prompt.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from atar_core.paths import _atar_home as atar_home

NUDGE_STATE_PATH = os.path.join(atar_home(), "memory_nudge.json")

# Default intervals
REVIEW_INTERVAL_HOURS = 24       # Nudge every 24 hours
MIN_ENTRIES_TO_NUDGE = 5         # Don't nudge unless 5+ active entries
STALE_ENTRY_DAYS = 14            # Flag entries older than 14 days as stale
MAX_ENTRIES_BEFORE_PRUNE = 50    # Suggest pruning if >50 entries


@dataclass
class NudgeState:
    """Persistent state for memory nudge tracking."""
    last_nudge_at: float = 0.0
    last_review_at: float = 0.0
    nudge_count: int = 0
    entries_at_last_review: int = 0

    def to_dict(self) -> dict:
        return {
            "last_nudge_at": self.last_nudge_at,
            "last_review_at": self.last_review_at,
            "nudge_count": self.nudge_count,
            "entries_at_last_review": self.entries_at_last_review,
        }

    @classmethod
    def from_dict(cls, d: dict) -> NudgeState:
        return cls(
            last_nudge_at=d.get("last_nudge_at", 0.0),
            last_review_at=d.get("last_review_at", 0.0),
            nudge_count=d.get("nudge_count", 0),
            entries_at_last_review=d.get("entries_at_last_review", 0),
        )


def _load_state() -> NudgeState:
    try:
        import json
        with open(NUDGE_STATE_PATH) as f:
            return NudgeState.from_dict(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return NudgeState()


def _save_state(state: NudgeState) -> None:
    import json
    os.makedirs(os.path.dirname(NUDGE_STATE_PATH), exist_ok=True)
    with open(NUDGE_STATE_PATH, "w") as f:
        json.dump(state.to_dict(), f)


def should_nudge() -> bool:
    """Check if it's time to nudge the user about memory review."""
    state = _load_state()
    now = time.time()

    # Don't nudge if recently nudged (within interval)
    hours_since_nudge = (now - state.last_nudge_at) / 3600
    if hours_since_nudge < REVIEW_INTERVAL_HOURS:
        return False

    # Don't nudge if user recently reviewed
    hours_since_review = (now - state.last_review_at) / 3600
    if hours_since_review < REVIEW_INTERVAL_HOURS:
        return False

    # Check if there are enough entries to warrant a review
    from atar_core.memory import count_active
    active_count = count_active()
    if active_count < MIN_ENTRIES_TO_NUDGE:
        return False

    # Record the nudge
    state.last_nudge_at = now
    state.nudge_count += 1
    state.entries_at_last_review = active_count
    _save_state(state)
    return True


def mark_reviewed() -> None:
    """Mark that user has reviewed memories."""
    state = _load_state()
    state.last_review_at = time.time()
    from atar_core.memory import count_active
    state.entries_at_last_review = count_active()
    _save_state(state)


def get_nudge_summary() -> str | None:
    """Generate a summary for the nudge prompt. Returns formatted text or None."""
    from atar_core.memory import count_active, get_entries

    active_count = count_active()
    if active_count == 0:
        return None

    entries = get_entries(limit=20)
    if not entries:
        return None

    lines = ["[bold]Memory Review[/]", ""]

    # Count by category
    categories: dict[str, int] = {}
    for e in entries:
        cat = e.category or "fact"
        categories[cat] = categories.get(cat, 0) + 1

    lines.append(f"Total entries: {active_count}")
    for cat, count in sorted(categories.items()):
        lines.append(f"  {cat}: {count}")

    # Show last 5 entries
    lines.append("")
    lines.append("[bold]Recent entries:[/]")
    for e in entries[:5]:
        age = time.time() - e.updated_at
        age_str = f"{age/86400:.0f}d ago" if age > 86400 else f"{age/3600:.0f}h ago"
        stale = " [yellow]⚠ stale[/]" if age/86400 > STALE_ENTRY_DAYS else ""
        lines.append(f"  [{e.category}] {e.content[:80]}{stale} [dim]({age_str})[/]")

    # Stale entries warning
    stale_count = sum(
        1 for e in entries
        if (time.time() - e.updated_at) / 86400 > STALE_ENTRY_DAYS
    )
    if stale_count > 0:
        lines.append("")
        lines.append(f"[yellow]⚠ {stale_count} entries are older than {STALE_ENTRY_DAYS} days[/]")

    # Prune suggestion
    if active_count > MAX_ENTRIES_BEFORE_PRUNE:
        lines.append("")
        lines.append(f"[dim]Tip: You have {active_count} entries. Consider pruning with /memory forget [id].[/]")

    lines.append("")
    lines.append("[dim]Use /memory to review, /memory forget [id] to remove.[/]")

    return "\n".join(lines)


def get_nudge_stats() -> dict:
    """Return current nudge statistics for /status display."""
    state = _load_state()
    from atar_core.memory import count_active
    return {
        "active_entries": count_active(),
        "last_nudge_hours_ago": round((time.time() - state.last_nudge_at) / 3600, 1) if state.last_nudge_at else None,
        "last_review_hours_ago": round((time.time() - state.last_review_at) / 3600, 1) if state.last_review_at else None,
        "total_nudges": state.nudge_count,
    }
