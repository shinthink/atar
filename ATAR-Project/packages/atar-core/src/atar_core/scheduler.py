"""ATAR scheduler — persistent cron job store with background execution."""

from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from dataclasses import dataclass

from atar_core.paths import _atar_home as atar_home

DB_PATH = os.path.join(atar_home(), "memory.db")

_thread: threading.Thread | None = None
_running = False


@dataclass
class ScheduledJob:
    id: int = 0
    cron_expr: str = ""
    prompt: str = ""
    target_channel: str = "repl"
    enabled: bool = True
    last_run_at: float = 0.0
    next_run_at: float = 0.0
    created_at: float = 0.0
    failures: int = 0


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cron_expr TEXT NOT NULL DEFAULT '',
            prompt TEXT NOT NULL DEFAULT '',
            target_channel TEXT DEFAULT 'repl',
            enabled INTEGER DEFAULT 1,
            last_run_at REAL DEFAULT 0,
            next_run_at REAL DEFAULT 0,
            created_at REAL NOT NULL,
            failures INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


def _parse_simple_cron(expr: str) -> float | None:
    """Parse simple expressions: '30m', 'every 2h', 'cron-like', ISO timestamp."""
    m = re.match(r'(\d+)m', expr.strip())
    if m:
        return time.time() + int(m.group(1)) * 60
    m = re.match(r'every\s+(\d+)h', expr.strip())
    if m:
        return time.time() + int(m.group(1)) * 3600
    # Try ISO timestamp
    try:
        from datetime import datetime
        return datetime.fromisoformat(expr.strip()).timestamp()
    except ValueError:
        pass
    return time.time() + 300  # default 5 min


def add_job(cron_expr: str, prompt: str, target_channel: str = "repl") -> int:
    conn = _get_conn()
    now = time.time()
    next_run = _parse_simple_cron(cron_expr)
    cur = conn.execute(
        "INSERT INTO scheduled_jobs (cron_expr, prompt, target_channel, created_at, next_run_at, enabled) VALUES (?,?,?,?,?,1)",
        (cron_expr, prompt, target_channel, now, next_run),
    )
    conn.commit()
    return cur.lastrowid


def list_jobs() -> list[ScheduledJob]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM scheduled_jobs ORDER BY created_at DESC").fetchall()
    return [_row_to_job(r) for r in rows]


def remove_job(job_id: int) -> bool:
    conn = _get_conn()
    cur = conn.execute("DELETE FROM scheduled_jobs WHERE id=?", (job_id,))
    conn.commit()
    return cur.rowcount > 0


def set_enabled(job_id: int, enabled: bool) -> bool:
    conn = _get_conn()
    cur = conn.execute("UPDATE scheduled_jobs SET enabled=? WHERE id=?", (1 if enabled else 0, job_id))
    conn.commit()
    return cur.rowcount > 0


def record_failure(job_id: int) -> int:
    """Record a failure. Returns total failures. Disables after 2 failures."""
    conn = _get_conn()
    conn.execute("UPDATE scheduled_jobs SET failures = failures + 1 WHERE id=?", (job_id,))
    row = conn.execute("SELECT failures FROM scheduled_jobs WHERE id=?", (job_id,)).fetchone()
    failures = row["failures"] if row else 0
    if failures >= 2:
        conn.execute("UPDATE scheduled_jobs SET enabled=0 WHERE id=?", (job_id,))
    conn.commit()
    return failures


def _row_to_job(row) -> ScheduledJob:
    return ScheduledJob(
        id=row["id"], cron_expr=row["cron_expr"], prompt=row["prompt"],
        target_channel=row["target_channel"], enabled=bool(row["enabled"]),
        last_run_at=row["last_run_at"], next_run_at=row["next_run_at"],
        created_at=row["created_at"], failures=row["failures"],
    )


def start_scheduler(agent_factory=None) -> None:
    """Start background thread. Stops when _running = False."""
    global _thread, _running
    if _running:
        return
    _running = True
    def _loop() -> None:
        while _running:
            try:
                conn = _get_conn()
                now = time.time()
                due = conn.execute(
                    "SELECT * FROM scheduled_jobs WHERE enabled=1 AND next_run_at <= ? ORDER BY next_run_at ASC",
                    (now,)
                ).fetchall()
                for row in due:
                    job = _row_to_job(row)
                    try:
                        if agent_factory:
                            agent = agent_factory()
                            import asyncio
                            asyncio.run(agent.run(job.prompt))
                        conn.execute(
                            "UPDATE scheduled_jobs SET last_run_at=?, next_run_at=?, failures=0 WHERE id=?",
                            (now, _parse_simple_cron(job.cron_expr), job.id),
                        )
                    except Exception:
                        failures = record_failure(job.id)
                        # Notify target channel about failure
                conn.commit()
            except Exception:
                pass
            time.sleep(30)
    _thread = threading.Thread(target=_loop, daemon=True)
    _thread.start()


def stop_scheduler() -> None:
    global _running
    _running = False
