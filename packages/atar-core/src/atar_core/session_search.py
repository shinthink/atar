"""ATAR session search — FTS5 + cached LLM summaries."""

from __future__ import annotations

import os
import sqlite3
import time

from atar_core.paths import _atar_home as atar_home

DB_PATH = os.path.join(atar_home(), "memory.db")

SUMMARY_CACHE: dict[str, str] = {}
_llm_call_count = 0


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_summaries (
            session_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(session_id, title, messages)")
    conn.commit()
    return conn


def index_session(session_id: str, title: str, messages_text: str) -> None:
    conn = _get_conn()
    # Remove old index entry
    conn.execute("DELETE FROM sessions_fts WHERE session_id = ?", (session_id,))
    conn.execute(
        "INSERT INTO sessions_fts (session_id, title, messages) VALUES (?, ?, ?)",
        (session_id, title, messages_text),
    )
    conn.commit()


def get_summary(session_id: str) -> str | None:
    if session_id in SUMMARY_CACHE:
        return SUMMARY_CACHE[session_id]
    conn = _get_conn()
    row = conn.execute("SELECT summary FROM session_summaries WHERE session_id=?", (session_id,)).fetchone()
    if row:
        SUMMARY_CACHE[session_id] = row["summary"]
        return row["summary"]
    return None


def set_summary(session_id: str, summary: str) -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO session_summaries (session_id, summary, created_at) VALUES (?,?,?)",
        (session_id, summary, time.time()),
    )
    conn.commit()
    SUMMARY_CACHE[session_id] = summary


async def generate_summary(session_id: str, messages_text: str, provider=None) -> str:
    """Generate LLM summary for a session. Caches result."""
    global _llm_call_count
    cached = get_summary(session_id)
    if cached:
        return cached
    if not provider:
        summary = f"Session {session_id[:8]} ({len(messages_text)} chars)"
    else:
        try:
            prompt = f"Summarize this conversation in ONE sentence (max 120 chars):\n\n{messages_text[:2000]}"
            # Use provider directly — skip agent loop
            from atar_models.requests import Message, ModelRequest
            req = ModelRequest(provider_id="", model="", messages=[
                Message(role="user", content=prompt),
            ])
            _llm_call_count += 1
            text = ""
            async for event in provider.stream(req):
                if hasattr(event, "text") and event.text:
                    text += event.text
            summary = text.strip()[:200] or f"Session {session_id[:8]}"
        except Exception:
            summary = f"Session {session_id[:8]} ({len(messages_text)} chars)"
    set_summary(session_id, summary)
    return summary


def search_sessions(query: str, limit: int = 10) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT session_id, title, snippet(sessions_fts, 2, '<b>', '</b>', '...', 32) as snippet FROM sessions_fts WHERE sessions_fts MATCH ? ORDER BY rank LIMIT ?",
        (query, limit),
    ).fetchall()
    results = []
    for r in rows:
        summary = get_summary(r["session_id"])
        results.append({
            "session_id": r["session_id"],
            "title": r["title"],
            "snippet": r["snippet"] or "",
            "summary": summary or "",
        })
    return results


def get_llm_call_count() -> int:
    return _llm_call_count
