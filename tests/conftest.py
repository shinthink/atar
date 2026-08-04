"""ATAR test suite configuration."""

import sqlite3

import pytest


@pytest.fixture(autouse=True)
def _clean_memory_db():
    """Clean memory/scheduler DB between test runs for isolation."""
    import os
    db_path = os.path.expanduser("~/.atar/memory.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM memory_entries")
        conn.execute("DELETE FROM scheduled_jobs")
        conn.commit()
        conn.close()
    yield
