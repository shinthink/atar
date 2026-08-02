# ATAR v0.1.0 — Release Notes

**Date:** 2026-08-02  
**Blueprint:** ATAR_TERMINAL_SUPERIORITY_BLUEPRINT.md V4  
**Status:** Released (controlled v0.1)

## Summary
First functional release of ATAR Terminal. AI-powered CLI agent with chat, planning, code analysis, session persistence, and 5 built-in tools.

## Metrics
| Category | Count |
|----------|-------|
| Python files | 44 |
| Packages | 29 (9 with implementation) |
| Tools | 5 (read_file, write_file, terminal, git, run_tests) |
| Contract tests | 33 |
| Integration tests | 4 |
| ADRs | 4 |
| Research files | 8 |
| Ruff errors | 2 (E501, non-blocking) |
| CLI commands | chat, plan, code, init |

## Blueprint Coverage
| Section | Milestone | Status |
|---------|-----------|--------|
| 1-4 | Foundation + Architecture | ✅ |
| 5 | Repository + CI | ✅ |
| 6 | Provider System | ✅ Anthropic adapter |
| 7 | TUI | ⚠ Skeleton only |
| 8-9 | Agent Core | ✅ State machine, event bus |
| 10 | Planning | ✅ Risk classification |
| 11 | Tools | ✅ 5 tools |
| 12-13 | Security + Storage | ⚠ JSON, not SQLite |
| 14-15 | Context + Memory | ⚠ Sessions only |
| 16 | Code Intelligence | ⚠ Git + test tools |
| 17+ | Evidence, Multi-agent, Browser, etc. | ❌ Deferred |

**Product readiness:** ~20% of v1.0 terminal scope.
