# ATAR — Current Milestone

**Milestone:** 4 — Async Core + Typed Events + Storage + Secrets + Audit + TUI Shell
**Blueprint reference:** Section 64, Step 4
**Started:** 2026-08-01
**Status:** In progress

## Objective
Build the async core runtime with typed event system, storage layer (SQLite + Alembic), secrets management, audit logging, and TUI shell skeleton.

## Prerequisites
- [x] Milestone 3: Repository, docs, CI
- [ ] Research: asyncio/AnyIO patterns
- [ ] Research: SQLAlchemy async + SQLite WAL
- [ ] Research: Textual framework
- [ ] ADR-002: async core and event system
- [ ] ADR-003: storage strategy
- [ ] ADR-004: secrets architecture

## Deliverables
1. `atar_core/event_bus.py` — typed event emitter with subscriber registration
2. `atar_core/state_machine.py` — agent state transitions (IDLE → ... → COMPLETED)
3. `atar_storage/` — SQLAlchemy async sessions, Alembic migrations
4. `atar_security/secrets.py` — OS keyring + encrypted file provider
5. `atar_security/audit.py` — correlation-ID audit logger
6. `atar_tui/app.py` — Textual App skeleton with navigation
7. Contract tests for event bus, state machine, storage, secrets

## Risks
- SQLAlchemy async with SQLite has edge cases with WAL mode concurrency
- Secrets API may not be available on all platforms (fallback to env vars)
- Textual 8.x may have breaking changes from documentation

## Blocked by
- None currently
