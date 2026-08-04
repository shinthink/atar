"""ATAR central paths — single source of truth for all ATAR directories."""

from __future__ import annotations

import os
from pathlib import Path


def _atar_home() -> Path:
    """ATAR home directory: ~/.atar by default, override with ATAR_HOME."""
    env = os.environ.get("ATAR_HOME", "")
    if env:
        return Path(env).expanduser().resolve()
    return Path.home() / ".atar"


def atar_config_dir(profile: str = "default") -> Path:
    """Config directory for a profile."""
    if profile in ("default", ""):
        return _atar_home()
    return _atar_home() / "profiles" / profile


def atar_data_dir(profile: str = "default") -> Path:
    """Data directory (sessions, memory, checkpoints)."""
    base = atar_config_dir(profile)
    return base / "data"


def atar_skills_dir(profile: str = "default") -> Path:
    """User skills directory."""
    return atar_config_dir(profile) / "skills"


def atar_plugins_dir(profile: str = "default") -> Path:
    """User plugins directory."""
    return atar_config_dir(profile) / "plugins"


def atar_logs_dir(profile: str = "default") -> Path:
    """Logs directory."""
    return atar_config_dir(profile) / "logs"


def atar_sessions_db(profile: str = "default") -> Path:
    """SQLite session database path."""
    return atar_data_dir(profile) / "sessions.db"


def atar_config_file(profile: str = "default") -> Path:
    """Config YAML file path."""
    return atar_config_dir(profile) / "config.yaml"


def atar_memory_file(profile: str = "default") -> Path:
    """Memory file path."""
    return atar_data_dir(profile) / "memory.db"


def ensure_dirs(profile: str = "default") -> None:
    """Create all required directories."""
    for d in [
        atar_config_dir(profile),
        atar_data_dir(profile),
        atar_skills_dir(profile),
        atar_plugins_dir(profile),
        atar_logs_dir(profile),
    ]:
        d.mkdir(parents=True, exist_ok=True)
