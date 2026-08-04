"""ATAR complexity router — route simple tasks to cheap models, complex to expensive."""

from __future__ import annotations

import re

# Heuristic signals
_SIMPLE_SIGNALS = [
    r"\b(?:apa|what|who|siapa|kapan|when)\b",  # factoid questions
]
_COMPLEX_SIGNALS = [
    r"\b(?:refactor|debug|analisa|mendalam|multi.?file)\b",
    r"\b(?:buatkan|create|build|tulis|write).*(?:aplikasi|app|sistem|system)\b",
]


def estimate_complexity(prompt: str, tool_call_history: int = 0) -> str:
    """Return 'simple' or 'complex' based on heuristics."""
    text = prompt.lower()
    if any(re.search(p, text) for p in _COMPLEX_SIGNALS):
        return "complex"
    if tool_call_history >= 3:
        return "complex"
    if len(prompt.split()) < 10 and any(re.search(p, text) for p in _SIMPLE_SIGNALS):
        return "simple"
    return "complex"  # default to complex for safety


def load_route_config() -> dict:
    import json, os
    from atar_core.paths import _atar_home
    try:
        with open(os.path.join(_atar_home(), "config.json")) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    return {
        "enabled": cfg.get("auto_routing", False),
        "simple_model": cfg.get("simple_model", "deepseek-chat"),
        "complex_model": cfg.get("complex_model", "deepseek-v4-pro"),
    }
