"""ATAR hooks system — event-driven callbacks via hooks.json."""

from __future__ import annotations

import json
import os
import subprocess

HOOKS_PATH = os.path.expanduser("~/.atar/hooks.json")


def load_hooks() -> dict[str, list[str]]:
    try:
        with open(HOOKS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def fire_hook(event: str, payload: dict) -> None:
    """Fire a hook event. Runs shell commands from hooks.json."""
    hooks = load_hooks().get(event, [])
    for cmd in hooks:
        try:
            subprocess.run(
                cmd, shell=True, capture_output=True, timeout=10,
                input=json.dumps(payload), text=True,
            )
        except Exception:
            pass  # hooks are fire-and-forget
