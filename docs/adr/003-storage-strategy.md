# ADR-003: Storage Strategy — SQLite + SQLAlchemy Async + Alembic

## Status
Accepted

## Context
ATAR Terminal v1.0 is local-first with no required network service. The blueprint Section 13 specifies SQLite with WAL mode and FTS5, managed through SQLAlchemy ORM, with Alembic for migrations. Sessions, plans, tasks, memory, audit events, and project metadata must be persisted locally.

## Decision
Use **SQLite** with **WAL journal mode** and **FTS5** full-text search, accessed through **SQLAlchemy 2.0 async** with **aiosqlite** driver, and **Alembic** for schema migrations.

### Architecture
```
atar_storage/
├── engine.py         — AsyncEngine factory with WAL pragmas
├── session.py        — AsyncSession context manager
├── base.py           — SQLAlchemy declarative Base
├── models/           — ORM models (Session, Plan, Task, Memory, AuditEvent)
├── repositories/     — Repository protocol implementations
├── migrations/       — Alembic migration scripts
└── fts.py            — FTS5 index management for memory search
```

### WAL Mode Configuration
```python
engine = create_async_engine(
    "sqlite+aiosqlite:///data/atar.sqlite3",
    connect_args={
        "check_same_thread": False,
    },
)
# Enable WAL via event listener
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### Repository Pattern
Every storage access goes through a repository implementing the `SessionRepository` protocol from `atar_protocols`:
```python
class SqliteSessionRepository:
    async def get(self, session_id: UUID) -> Session | None: ...
    async def save(self, session: Session) -> None: ...
    async def list(self, limit: int = 20) -> list[Session]: ...
```

## Consequences
- Single-file database — zero configuration for users.
- WAL mode enables concurrent reads while writes are serialized (acceptable for single-user v1.0).
- FTS5 provides full-text search for memory and session content.
- Alembic migrations ensure schema versioning across releases.
- No connection pooling needed for single-user SQLite.
- All async queries run on the same event loop thread (no thread pool needed with aiosqlite).

## Alternatives Considered
1. **PostgreSQL embedded** — rejected because it adds deployment complexity for v1.0 terminal-only product.
2. **SQLite with synchronous sqlite3** — rejected because async-native runtime requires non-blocking I/O.
3. **File-based JSON/msgpack storage** — rejected because no query support, no migrations, no FTS.
4. **DuckDB** — rejected because it adds a heavy dependency for v1.0; SQLite suffices.

## References
- Blueprint Section 13 (Storage and Session Persistence)
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/fts5.html
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- https://alembic.sqlalchemy.org/
