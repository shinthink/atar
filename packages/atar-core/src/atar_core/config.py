"""ATAR configuration — YAML-based with profiles, no secrets in config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from atar_core.paths import atar_config_file, ensure_dirs

DEFAULT_CONFIG = {
    "config_version": 1,
    "model": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.7,
    },
    "fallback": {
        "enabled": True,
        "providers": ["openai", "anthropic"],
        "max_attempts": 3,
    },
    "agent": {
        "max_turns": 8,
        "max_tool_calls": 20,
        "max_time_seconds": 300,
    },
    "display": {
        "theme": "atar",
        "status_bar": True,
        "banner": True,
    },
    "terminal": {
        "backend": "local",
        "timeout_default": 30,
        "safe_env": True,
    },
    "security": {
        "require_approval": True,
        "workspace_roots": [os.getcwd()],
        "allowed_hosts": [],
    },
    "sessions": {
        "persist": True,
        "auto_resume": False,
        "max_history": 1000,
    },
    "context": {
        "max_tokens": 128000,
        "compression_enabled": False,
        "compression_threshold": 0.8,
    },
    "memory": {
        "enabled": True,
        "max_entries": 100,
        "review_interval_hours": 24,
    },
    "skills": {"enabled": True, "auto_load": True},
    "delegation": {"enabled": False, "max_children": 3, "max_depth": 1},
    "plugins": {"enabled": False, "trust_project": False},
    "mcp": {"enabled": False, "servers": []},
    "scheduler": {"enabled": False},
    "observability": {"log_level": "info", "telemetry": False},
}


@dataclass
class ATARConfig:
    """Resolved ATAR configuration for a profile."""
    profile: str = "default"
    config_path: Path = field(default_factory=Path)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def model(self) -> dict[str, Any]:
        return self.raw.get("model", {})

    @property
    def agent(self) -> dict[str, Any]:
        return self.raw.get("agent", {})

    @property
    def security(self) -> dict[str, Any]:
        return self.raw.get("security", {})

    @property
    def sessions(self) -> dict[str, Any]:
        return self.raw.get("sessions", {})

    @property
    def display(self) -> dict[str, Any]:
        return self.raw.get("display", {})


def load_config(profile: str = "default") -> ATARConfig:
    """Load configuration for a profile, creating default if missing."""
    ensure_dirs(profile)
    path = atar_config_file(profile)
    if not path.exists():
        _write_default(path)
        return ATARConfig(profile=profile, config_path=path, raw=_deep_copy(DEFAULT_CONFIG))

    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    # Merge with defaults for missing keys
    merged = _deep_copy(DEFAULT_CONFIG)
    _deep_merge(merged, raw)
    return ATARConfig(profile=profile, config_path=path, raw=merged)


def _deep_copy(d: dict) -> dict:
    import copy
    return copy.deepcopy(d)


def save_config(config: ATARConfig) -> None:
    """Save configuration to disk."""
    config.config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config.config_path, "w") as f:
        yaml.safe_dump(config.raw, f, default_flow_style=False)


def _write_default(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(DEFAULT_CONFIG, f, default_flow_style=False)


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
