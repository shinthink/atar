"""ATAR background task config — cheap provider routing, throttle, toggles."""

from __future__ import annotations

import json
import os

from atar_core.paths import _atar_home as atar_home

CONFIG_PATH = os.path.join(atar_home(), "config.json")


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get_background_provider_config() -> tuple[str, str]:
    """Returns (provider_id, model) for background tasks. Empty = disabled."""
    cfg = _load_config()
    bp = cfg.get("background_provider", "")
    bm = cfg.get("background_model", "")
    return bp, bm


def get_throttle() -> int:
    """How many turns between background task triggers (default 5)."""
    return _load_config().get("background_throttle", 5)


# ── Per-session toggles ──
_memory_enabled: bool = True
_skills_auto_enabled: bool = True


def is_memory_enabled() -> bool:
    return _memory_enabled


def toggle_memory() -> bool:
    global _memory_enabled
    _memory_enabled = not _memory_enabled
    return _memory_enabled


def is_skills_auto_enabled() -> bool:
    return _skills_auto_enabled


def toggle_skills_auto() -> bool:
    global _skills_auto_enabled
    _skills_auto_enabled = not _skills_auto_enabled
    return _skills_auto_enabled


# ── Background token tracking ──
_bg_tokens: dict[str, int] = {"memory": 0, "skill": 0}


def record_bg_tokens(category: str, count: int) -> None:
    _bg_tokens[category] = _bg_tokens.get(category, 0) + count


def get_bg_tokens() -> dict[str, int]:
    return dict(_bg_tokens)


def reset_bg_tokens() -> None:
    for k in _bg_tokens:
        _bg_tokens[k] = 0
