# ATAR IMPLEMENTATION VS BLUEPRINT AUDIT
Generated from live repository inspection at /root/ATAR-Project/

## EXECUTIVE SUMMARY

Entry point: `atar_cli.main:app` (Typer)
Default behavior: `atar` → Rich REPL with Hermes-style two-column banner
TUI behavior: `atar --tui` → Textual 27-screen TUI
Tests: 39/39 · RUFF: 0 errors
Git: pushed to shinthink/atar

## DETAILED FINDINGS

### F-001: FOUR EMPTY PROVIDER PACKAGES
- **Blueprint:** §4 — Provider Architecture
- **Status:** STUB
- **Files:** `providers/atar-provider-openai/` (0 py), `providers/atar-provider-openrouter/` (0 py), `providers/atar-provider-zai/` (0 py), `providers/atar-provider-custom/` (0 py)
- **Impact:** Only DeepSeek + Anthropic providers are usable; 4 of 6 blueprint providers are empty
- **Risk:** Users can't use OpenAI, OpenRouter, Z.AI, or custom providers
- **Fix:** Create client.py for each missing provider using OpenAI-compatible API
- **Tests needed:** Provider contract tests for each new provider
- **Acceptance:** `atar --provider openai` works

### F-002: ATAR_PLANNING PACKAGE IS EMPTY
- **Blueprint:** §11 — Planning System
- **Status:** PARTIAL (planning logic lives in atar-core)
- **File:** `packages/atar-planning/` — 0 files; `packages/atar-core/src/atar_core/planning.py` — exists
- **Impact:** Planning engine works but is misplaced in core rather than its own package
- **Fix:** Move planning.py to atar-planning package or remove empty package

### F-003: PROVIDER HARDCODED IN CHAT/TUI SCREENS
- **Blueprint:** §4 — Provider Configuration
- **Status:** BUG
- **Files:** `apps/atar-tui/src/atar_tui/app.py:194,428,466`, `apps/atar-cli/src/atar_cli/rich_repl.py:99`
- **Evidence:** `DeepSeekProvider(api_key=key, model="deepseek-chat")` hardcoded in 4 places
- **Impact:** Model picker switches agent but provider remains DeepSeek; switching to OpenAI fails
- **Fix:** Read provider/model from config, create provider dynamically
- **Acceptance:** Switching model via /model actually changes the active provider

### F-004: SESSION PERSISTENCE NOT VERIFIED
- **Blueprint:** §15 — Session Store
- **Status:** UNVERIFIED
- **File:** `packages/atar-core/src/atar_core/session.py` — 17 methods, JSON-backed
- **Evidence:** Session files exist but no automated test for persistence across restart
- **Impact:** Unknown if sessions survive restart
- **Tests needed:** `test_session_persist_across_restart`

### F-005: REPL SHOWS BARE TEXT — NO TOOL PROGRESS CARDS
- **Blueprint:** §12 — Tool and Agent Streaming
- **Status:** PARTIAL
- **File:** `apps/atar-cli/src/atar_cli/rich_repl.py:103-140`
- **Evidence:** REPL uses `console.print(t, end="")` for streaming but doesn't show tool execution progress
- **Impact:** When agent uses write_file/read_file/terminal tools, no progress cards appear
- **Fix:** Add `on_tool_call` and `on_tool_result` callbacks that render Obsidian panels
- **Acceptance:** User sees ✍️ write_file panels when agent uses tools

### F-006: NO EVIDENCE/VERIFICATION WORKFLOW IN REPL
- **Blueprint:** §12 — Evidence Before Completion
- **Status:** MISSING
- **Impact:** Agent can claim success without verification; no evidence cards
- **Required:** Verification checkmark cards after each tool execution

### F-007: 27 SCREEN CLASSES, ONLY ~12 CONNECTED
- **Blueprint:** §5 — TUI Design
- **File:** `apps/atar-tui/src/atar_tui/app.py`
- **Status:** PARTIAL
- **Connected:** Chat, Plan, Setup, Provider, Sessions, Tasks, Files, Terminal, Memory, MCP, Search, Audit, Settings, Diagnostics, Skills, Checkpoints (16)
- **Placeholder:** Welcome, Agents, Diff (shows git diff though), Process, Browser, Plugins (6)
- **Impact:** TUI has placeholder screens that show static text
- **Acceptance:** All screens show live data from corresponding backend

### F-008: PLANNING ENGINE EXISTS BUT PLANNING UI IS MINIMAL
- **Blueprint:** §11 — Planning Interface
- **Status:** PARTIAL
- **File:** `apps/atar-tui/src/atar_tui/app.py:PlanScreen`
- **Evidence:** PlanScreen generates plans, shows risk icons, allows approve/reject/execute
- **Missing:** Task DAG visualization, dependency graph, plan versioning, plan diff
- **Acceptance:** PlanScreen shows task graph with dependencies

## COMPLETED REQUIREMENTS (Verified)

| Blueprint § | Feature | Evidence |
|------------|---------|----------|
| §2 | `atar` entry point | `atar_cli.main:app` → Typer callback |
| §3 | Non-TTY behavior | `_is_interactive()` check, `atar --run`, `atar --cli` |
| §4 | DeepSeek provider | `providers/atar-provider-deepseek/client.py` — streaming + tool calling |
| §4 | Anthropic provider | `providers/atar-provider-anthropic/client.py` — SSE streaming |
| §4 | Provider capabilities | `capabilities()` returns text/streaming/tools |
| §5 | Textual TUI | `ATARApp(App)` with 27 screens |
| §6 | Chat screen | Streaming chat with tool call display |
| §7 | Rich REPL | `rich_repl.py` — Hermes banner, prompt_toolkit, streaming |
| §8 | Slash autocomplete | `WordCompleter` with 12 commands + meta descriptions |
| §9 | Model picker | `/model` shows 5 models, keyboard selection |
| §9 | Session switcher | `/sessions` lists sessions, resume with messages |
| §10 | First-run setup | `SetupScreen` — 6 providers, key input, auth test, keyring |
| §11 | Planning engine | `PlanningEngine` generates plans with risk classification |
| §12 | Tool streaming | DeepSeek OpenAI tool_use → tool_call events → execution |
| §13 | Session store | `SessionManager` with JSON persistence |
| §14 | Secrets | `secrets.py` — keyring primary, env fallback |
| §18 | Tests | 39/39 — contract, integration, PTY tests |

## PRIORITY FIX ORDER

1. **F-003** — Provider hardcoding → read from config (blocks model switching)
2. **F-005** — Tool progress cards in REPL streaming (UX gap)
3. **F-001** — Empty provider packages (feature completeness)
4. **F-004** — Session persistence test (reliability)
5. **F-007** — Remaining placeholder screens (UI completeness)
