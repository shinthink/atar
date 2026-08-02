"""ATAR config reader — resolve secrets from env or config file."""

from __future__ import annotations

import os


def get_api_key() -> str:
    """Resolve API key from environment or config file."""
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
    if key:
        return key
    # Fallback to config file
    import json
    config_path = os.path.expanduser("~/.atar/config.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
            return cfg.get("api_key", "")
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return ""


def save_api_key(key: str) -> None:
    """Save API key to config file."""
    import json
    config_dir = os.path.expanduser("~/.atar")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.json")
    cfg = {}
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    cfg["api_key"] = key
    with open(config_path, "w") as f:
        json.dump(cfg, f)
