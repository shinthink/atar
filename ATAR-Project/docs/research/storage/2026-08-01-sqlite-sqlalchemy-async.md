# Research: SQLite + SQLAlchemy Async + WAL + Alembic

## Metadata
- **Research date:** 2026-08-01
- **Official documentation URL:** https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Secondary official URLs:**
  - https://www.sqlite.org/wal.html
  - https://www.sqlite.org/fts5.html
  - https://alembic.sqlalchemy.org/en/latest/
  - https://github.com/omnilib/aiosqlite
- **SDK/package versions reviewed:** SQLAlchemy 2.0.51, aiosqlite 0.21, Alembic 1.15, greenlet 3.0
- **Research owner:** Lead Architect
- **Reviewer:** Pending

## Purpose in ATAR
ATAR Terminal v1.0 requires local session persistence, plan/task storage, memory storage, and audit logging. Per ADR-003, SQLite with WAL mode accessed via SQLAlchemy 2.0 async + aiosqlite, migrated with Alembic.

## Official Terminology
- **WAL (Write-Ahead Log):** SQLite journal mode where changes are written to a separate WAL file before being transferred back to the database via checkpointing
- **Checkpointing:** The process of transferring WAL content back to the main database file
- **AsyncEngine:** SQLAlchemy's async wrapper around Engine using `create_async_engine()`
- **AsyncSession:** SQLAlchemy's async ORM session
- **aiosqlite:** Async wrapper around Python's sqlite3 module using a background thread
- **FTS5:** SQLite's full-text search engine
- **greenlet:** C extension required by SQLAlchemy async for coroutine integration

## Authentication
N/A — local database, no authentication required. Database file permissions (0600) provide access control.

## Network Contract
N/A — local file-based. WAL mode does NOT work over network filesystems (all processes must share memory on same host).

## WAL Mode Behavior
- **Concurrency:** Readers do not block writers, writers do not block readers. Only ONE writer at a time.
- **Performance:** WAL is significantly faster than rollback journal in most scenarios
- **Checkpointing:** Automatic at 1000 pages by default. Can be manual or disabled
- **Files created:** `.sqlite3-wal` (WAL file) and `.sqlite3-shm` (shared memory index)
- **Sync behavior:** Writers sync on every commit with `PRAGMA synchronous=FULL`; NORMAL omits write sync but checkpoints still sync

## aiosqlite Specifics
- Runs sqlite3 in a dedicated background thread — all queries are non-blocking
- `check_same_thread=False` must be passed as connect arg (default sqlite3 enforces same-thread)
- Connection pool size should be 1 for single-user SQLite (more connections = contention)

## SQLAlchemy Async Pattern
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine("sqlite+aiosqlite:///data/atar.sqlite3")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async with async_session() as session:
    async with session.begin():
        session.add(obj)
```

## Alembic Async Migrations
- Use `alembic init -t async migrations`
- Migration env.py must use `run_async()` helper
- `alembic upgrade head` and `alembic downgrade -1` must be tested

## Known Incompatibilities
- WAL does NOT work over NFS or network filesystems
- `aiosqlite` uses a background thread — true async I/O is not possible with SQLite
- Long-running read transactions can prevent checkpoint progress
- Cannot change `page_size` after entering WAL mode

## Security Requirements
- Database file permissions: 0600 (owner read/write only)
- Secrets must NEVER be stored in SQLite (per ADR-004)
- Audit logs must redact credentials before storage
- FTS5 indexes must not expose sensitive content through full-text search

## Required Contract Tests
1. Engine creation and connection
2. Session CRUD (create, read, update, delete)
3. Concurrent read/write with WAL
4. Alembic upgrade/downgrade
5. FTS5 search
6. Transaction rollback
7. Connection failure handling

## Open Questions
- None — all confirmed via official docs

## Implementation Decision
Proceed per ADR-003 with SQLAlchemy 2.0 async + aiosqlite + WAL + Alembic.

## Evidence
- SQLAlchemy docs confirmed: `create_async_engine` with `sqlite+aiosqlite://`
- SQLite WAL docs confirmed: readers don't block writers, checkpoint at 1000 pages
- aiosqlite confirmed: `check_same_thread=False` required
- Alembic confirmed: async template via `alembic init -t async`
