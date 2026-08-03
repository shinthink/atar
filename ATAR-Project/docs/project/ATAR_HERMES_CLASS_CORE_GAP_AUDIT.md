# ATAR Hermes-Class Core Gap Audit

## ATAR State (post P0/P1 repair)
- **Commit**: 931935b
- **Version**: 0.1.0
- **Tests**: 60 passing
- **P0/P1 gates**: ALL PASS

## Subsystem Audit

| Subsystem | Status | Priority |
|-----------|--------|----------|
| Config/Profiles | MISSING — hardcoded env vars only | M1 |
| Agent Kernel | PARTIAL — message roles fixed, no budgets/cancellation | M2 |
| Prompt Assembly | MISSING — one string in repl | M3 |
| Context Engine/Compression | MISSING | M3 |
| Provider Registry | PARTIAL — router exists, no profiles/discovery | M4 |
| Tools/Toolsets | PARTIAL — 6 tools, no toolsets | M5 |
| Plugins/Hooks | MISSING | M5 |
| Sessions/Search | PARTIAL — sqlite_store exists, no FTS search | M6 |
| REPL | PARTIAL — works, no command registry | M7 |
| Memory | MISSING | M8 |
| Skills | MISSING | M8 |
| Checkpoints | MISSING | M9 |
| Background/Queue/Steer | MISSING | M10 |
| Delegation | MISSING | M11 |
| Goals | MISSING | M11 |
| Durable Tasks | MISSING | M12 |
| MCP | MISSING | M13 |
| Browser | STUB — browser tools registered but not implemented | M13 |
| Security | PARTIAL — P0/P1 done, need full re-audit | M15 |
| Packaging | PARTIAL — works with uv, no wheel build test | M0 |
