"""ATAR memory — bounded persistent knowledge store."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from atar_core.paths import atar_memory_file, ensure_dirs

MAX_ENTRIES = 100
MAX_ENTRY_LENGTH = 500
MAX_TOTAL_CHARS = 5000


@dataclass
class MemoryEntry:
    content: str
    category: str = "general"  # user, technical, preference, correction
    created_at: str = ""
    usage_count: int = 0


def _load_memories(profile: str = "default") -> list[MemoryEntry]:
    path = atar_memory_file(profile)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return [MemoryEntry(**item) for item in data if isinstance(item, dict)]
    except (json.JSONDecodeError, KeyError):
        return []


def _save_memories(entries: list[MemoryEntry], profile: str = "default") -> None:
    ensure_dirs(profile)
    path = atar_memory_file(profile)
    with open(path, "w") as f:
        json.dump([{"content": e.content, "category": e.category, "created_at": e.created_at, "usage_count": e.usage_count} for e in entries], f, indent=2)


def add_memory(content: str, category: str = "general", profile: str = "default") -> bool:
    """Add a memory entry. Rejects duplicates. Returns True if added."""
    if len(content) > MAX_ENTRY_LENGTH:
        content = content[:MAX_ENTRY_LENGTH]
    entries = _load_memories(profile)

    # Reject exact duplicates
    if any(e.content == content for e in entries):
        return False

    # Cap total entries
    if len(entries) >= MAX_ENTRIES:
        entries.pop(0)

    # Cap total chars
    total = sum(len(e.content) for e in entries) + len(content)
    while total > MAX_TOTAL_CHARS and entries:
        total -= len(entries[0].content)
        entries.pop(0)

    import time
    entries.append(MemoryEntry(
        content=content,
        category=category,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    ))
    _save_memories(entries, profile)
    return True


def remove_memory(content_fragment: str, profile: str = "default") -> int:
    """Remove entries containing the fragment. Returns count removed."""
    entries = _load_memories(profile)
    before = len(entries)
    entries = [e for e in entries if content_fragment not in e.content]
    removed = before - len(entries)
    if removed:
        _save_memories(entries, profile)
    return removed


def list_memories(profile: str = "default") -> list[MemoryEntry]:
    return _load_memories(profile)


def memory_snapshot(max_chars: int = 2000, profile: str = "default") -> str:
    """Get a snapshot for prompt injection. Truncated to max_chars."""
    entries = _load_memories(profile)
    if not entries:
        return ""
    lines = []
    total = 0
    for e in entries:
        line = f"- {e.content}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line)
    return "User context (persistent memory):\n" + "\n".join(lines)


def memory_count(profile: str = "default") -> int:
    return len(_load_memories(profile))
