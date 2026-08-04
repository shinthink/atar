"""ATAR plan mode — read-only agent that builds plans, doesn't execute."""

from __future__ import annotations

_plan_mode = False


def is_plan_mode() -> bool:
    return _plan_mode


def toggle_plan() -> bool:
    global _plan_mode
    _plan_mode = not _plan_mode
    return _plan_mode
