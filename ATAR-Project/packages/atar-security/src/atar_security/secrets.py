"""ATAR secrets — keyring-first, environment, then config file."""

from __future__ import annotations

import json
import os

SERVICE = "atar"


def get_api_key(provider: str = "deepseek") -> str:
    """Resolve API key: keyring → env → config file."""
    # 1. Check keyring (secure, platform-native)
    try:
        import keyring
        key = keyring.get_password(SERVICE, provider)
        if key:
            return key
    except (ImportError, Exception):
        pass

    # 2. Check environment
    env_map = {
        "deepseek": ["DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "zai": ["ZAI_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
    }
    for var in env_map.get(provider, []):
        val = os.environ.get(var)
        if val:
            return val

    # 3. Fallback to config file (encrypted in production)
    config_path = os.path.expanduser("~/.atar/config.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
            return cfg.get(f"{provider}_api_key", cfg.get("api_key", ""))
    except (FileNotFoundError, json.JSONDecodeError):
        return ""

    return ""


def save_api_key(provider: str, key: str) -> bool:
    """Save API key: keyring first, then config fallback."""
    try:
        import keyring
        keyring.set_password(SERVICE, provider, key)
        return True
    except (ImportError, Exception):
        pass

    # Fallback: JSON config
    config_dir = os.path.expanduser("~/.atar")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.json")
    cfg = {}
    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    cfg[f"{provider}_api_key"] = key
    with open(config_path, "w") as f:
        json.dump(cfg, f)
    return True


def delete_api_key(provider: str) -> bool:
    """Remove API key from all stores."""
    try:
        import keyring
        keyring.delete_password(SERVICE, provider)
    except (ImportError, Exception):
        pass
    config_path = os.path.expanduser("~/.atar/config.json")
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        cfg.pop(f"{provider}_api_key", None)
        cfg.pop("api_key", None)
        with open(config_path, "w") as f:
            json.dump(cfg, f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return True


def is_first_run() -> bool:
    """Check if ATAR has been configured before."""
    config_path = os.path.expanduser("~/.atar/config.json")
    if not os.path.exists(config_path):
        return bool(get_api_key("deepseek"))
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        return not any(
            k.endswith("_api_key") or k == "provider"
            for k in cfg
        )
    except (json.JSONDecodeError, Exception):
        return True
