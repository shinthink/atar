"""ATAR structured memory — SQLite-backed, auditable, secret-filtered."""

from __future__ import annotations

import os
import re
import sqlite3
import time
from dataclasses import dataclass

from atar_core.paths import _atar_home as atar_home

DB_PATH = os.path.join(atar_home(), "memory.db")

# Regex patterns that look like secrets — reject on sight
SECRET_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9]{20,}'),
    re.compile(r'AKIA[A-Z0-9]{16}'),
    re.compile(r'Bearer [A-Za-z0-9_\-.]+=*'),
    re.compile(r'-----BEGIN (RSA |EC )?PRIVATE KEY-----'),
    re.compile(r'ghp_[A-Za-z0-9]{36}'),
    re.compile(r'glpat-[A-Za-z0-9\-_]{20,}'),
]

@dataclass
class MemoryEntry:
    id: int = 0
    category: str = "fact"
    content: str = ""
    source_session_id: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    confidence: float = 1.0
    superseded_by: int | None = None


def _is_secret(text: str) -> bool:
    for pat in SECRET_PATTERNS:
        if pat.search(text):
            return True
    return False


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL DEFAULT 'fact',
            content TEXT NOT NULL,
            source_session_id TEXT DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            confidence REAL DEFAULT 1.0,
            superseded_by INTEGER REFERENCES memory_entries(id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_category ON memory_entries(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_session ON memory_entries(source_session_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_active ON memory_entries(superseded_by) WHERE superseded_by IS NULL")
    conn.commit()
    return conn


def create_entry(category: str, content: str, source_session_id: str = "", confidence: float = 1.0) -> int | None:
    if _is_secret(content):
        import logging
        logging.getLogger("atar.memory").warning(f"Rejected secret-like memory entry: {content[:60]}...")
        return None
    now = time.time()
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO memory_entries (category, content, source_session_id, created_at, updated_at, confidence) VALUES (?,?,?,?,?,?)",
        (category, content, source_session_id, now, now, confidence),
    )
    conn.commit()
    return cur.lastrowid


def get_entries(category: str | None = None, query: str | None = None, limit: int = 30, active_only: bool = True) -> list[MemoryEntry]:
    conn = _get_conn()
    sql = "SELECT * FROM memory_entries WHERE 1=1"
    params: list = []
    if active_only:
        sql += " AND superseded_by IS NULL"
    if category:
        sql += " AND category = ?"
        params.append(category)
    if query:
        sql += " AND content LIKE ?"
        params.append(f"%{query}%")
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_entry(r) for r in rows]


def supersede_entry(entry_id: int, new_content: str) -> int | None:
    """Mark old entry superseded, create new one. Returns new entry ID."""
    if _is_secret(new_content):
        return None
    conn = _get_conn()
    old = conn.execute("SELECT * FROM memory_entries WHERE id=?", (entry_id,)).fetchone()
    if not old:
        return None
    now = time.time()
    # Create new entry
    cur = conn.execute(
        "INSERT INTO memory_entries (category, content, source_session_id, created_at, updated_at, confidence) VALUES (?,?,?,?,?,?)",
        (old["category"], new_content, old["source_session_id"], now, now, old["confidence"]),
    )
    new_id = cur.lastrowid
    # Mark old as superseded
    conn.execute("UPDATE memory_entries SET superseded_by=?, updated_at=? WHERE id=?", (new_id, now, entry_id))
    conn.commit()
    return new_id


def forget_entry(entry_id: int) -> bool:
    """Supersede with tombstone — never hard-delete."""
    return supersede_entry(entry_id, "[forgotten by user]") is not None


def count_active() -> int:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM memory_entries WHERE superseded_by IS NULL").fetchone()
    return row["cnt"] if row else 0


def _row_to_entry(row) -> MemoryEntry:
    return MemoryEntry(
        id=row["id"],
        category=row["category"],
        content=row["content"],
        source_session_id=row["source_session_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        confidence=row["confidence"] if row["confidence"] is not None else 1.0,
        superseded_by=row["superseded_by"],
    )


# Backward compat: re-export old API names
def list_memories() -> list[MemoryEntry]:
    return get_entries()

def add_memory(content: str, category: str = "fact") -> int | None:
    return create_entry(category=category, content=content)
