# Next Actions — Milestone 4

## Immediate (this session)

1. Create ADR-002 (async core and event system)
2. Create ADR-003 (storage strategy — SQLite + SQLAlchemy async + Alembic)
3. Create ADR-004 (secrets architecture)
4. Research file: `docs/research/storage/2026-08-01-sqlite-sqlalchemy-async.md`
5. Research file: `docs/research/tui/2026-08-01-textual.md`
6. Implement `atar_core/event_bus.py` with contract tests
7. Implement `atar_storage/` with Alembic migration and CRUD tests
8. Implement `atar_security/secrets.py` with OS keyring fallback
9. Implement `atar_security/audit.py` with correlation ID logging
10. Implement `atar_tui/app.py` — Textual skeleton with navigation

## After research gates pass

11. Provider research: 6 files under `docs/research/providers/`
12. ADR-005 through ADR-009 as needed
13. Contract tests for all new interfaces
14. Integration test: event bus → state machine → storage → audit

## Do NOT implement yet
- Planning engine
- Task graph
- Multi-agent
- Browser
- Voice
- MCP
- Skills/plugins
- Computer use
- Evaluation harness
