"""ATAR plugin system — auto-discover and load plugins at startup.

Plugins are Python packages under plugins/<category>/ with a register() function.
Categories: context-engines, memory, observability, providers, tools.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
CATEGORIES = ["context-engines", "memory", "observability", "providers", "tools"]


def discover_plugins() -> dict[str, list[str]]:
    """Discover all plugins across categories. Returns {category: [plugin_names]}."""
    result: dict[str, list[str]] = {}
    for cat in CATEGORIES:
        cat_dir = PLUGIN_DIR / cat
        if not cat_dir.exists():
            continue
        plugins = []
        for _, name, is_pkg in pkgutil.iter_modules([str(cat_dir)]):
            if is_pkg and not name.startswith("_"):
                plugins.append(name)
        if plugins:
            result[cat] = plugins
    return result


def load_plugin(category: str, name: str) -> object | None:
    """Import and return a plugin module. Returns None if not found."""
    try:
        mod = importlib.import_module(f"plugins.{category}.{name}")
        return mod
    except (ImportError, Exception):
        return None


def load_all() -> dict[str, list[object]]:
    """Discover and load all plugins. Returns {category: [loaded_modules]}."""
    discovered = discover_plugins()
    loaded: dict[str, list[object]] = {}
    for cat, names in discovered.items():
        mods = []
        for name in names:
            mod = load_plugin(cat, name)
            if mod:
                mods.append(mod)
        if mods:
            loaded[cat] = mods
    return loaded
