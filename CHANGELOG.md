# ATAR Changelog

## v0.7.0 — "Steel & Silk" (2026-08-04)

### Features
- **Streaming REPL** — streaming Markdown, tool progress cards, live status bar, slash-command autocomplete (20 commands)
- **Autonomous agent loop** — multi-turn tool calling with narration detection, auto-nudge, retry counter
- **12 tools**: read_file, write_file, patch, terminal, web_search, web_fetch, git, session_search, session_resume, delegate_task, run_tests, load_skill
- **6 providers**: DeepSeek, OpenAI, Anthropic, OpenRouter, Z.AI, Custom — with provider router and fallback
- **Two-level /model picker** — provider selection then model within provider
- **Memory system** — SQLite-backed, secret-filtered, auto-extraction via background LLM
- **FTS5 session search** — ranked full-text search across conversation history
- **Skills system** — auto-creation from sessions, registry, pending approval
- **Scheduler** — persistent cron jobs with enable/disable, failure tracking
- **Checkpoint system** — pre-mutation file snapshots, list/restore, undo/retry
- **Approval flow** — 5-choice interactive approval with diff preview, per-file/per-tool remember
- **Context compression** — non-recursive direct provider stream, token-efficient
- **Token efficiency (P1-P6)**: background token leak fix, prompt caching, output truncation, dynamic toolsets, complexity router, /cost breakdown
- **Interrupt-and-redirect** — Ctrl+C cancels current task with redirect prompt
- **CLI subcommands**: `atar doctor` (diagnose), `atar config`, `atar sessions`, `atar gateway`
- **Telegram gateway** — bot with allowlist security, streaming responses
- **User model** — local computation, no LLM required

### Architecture
- Python 3.12+, async-native (httpx + asyncio)
- Monorepo: 14 packages, 7 providers, 2 apps (CLI + TUI)
- SQLite for memory + sessions + scheduler + session search
- Safe environment: workspace-bounded file ops, SSRF-protected web fetch, process-tree kill
- Security: secret-filtered memory, audit logging, keyring-first credential resolution

### Quality
- **353 tests** (contract, integration, security, TUI/PTY)
- 65% coverage, 0 ruff warnings
- Security audited: 12 findings, 11 fixed
- Provider clients: all 6 fully implemented (shared OpenAI-compatible base)

---

## v0.6.0 — "Clarity Emerges" (2026-07)

- Rich REPL with streaming display
- DeepSeek multi-tool streaming fix
- Structured session persistence (SQLite)
- Provider registry with model updates from official docs
- Config system with profiles (YAML)
- Budgets: turn/tool/time limits
- Toolsets: composable tool groups with enable/disable
- Command registry: dynamic slash commands
- Prompt assembly: layered, cache-friendly

---

## v0.1.0 — "Clarity Begins" (2026-06)

- First controlled release
- Chat + Plan + Code modes
- DeepSeek API via Anthropic adapter
- Tools: read_file, write_file, terminal, git, test_runner
- 33 contract + integration tests
