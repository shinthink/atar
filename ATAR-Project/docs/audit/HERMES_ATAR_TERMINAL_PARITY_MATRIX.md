# HERMES-ATAR TERMINAL PARITY MATRIX

Generated: 2026-08-02 | ATAR commit: 206dd57 | Hermes: stable docs

## Category B — Classic Autonomous REPL

| ID | Feature | ATAR | Status | Gap |
|----|---------|------|--------|-----|
| B-01 | prompt_toolkit async input | `PromptSession` in `rich_repl.py:22` | PASS | — |
| B-02 | normal scrollback | No alt screen | PASS | — |
| B-03 | terminal-default bg | No forced bg | PASS | — |
| B-04 | compact banner | 8-line via `show_banner()` | PASS | — |
| B-05 | multiline editing | Alt+Enter via keybindings | PASS | — |
| B-06 | history | `enable_history_search=True` | PASS | — |
| B-07 | slash autocomplete | `WordCompleter` with 12 commands | PASS | — |
| B-08 | status bar | `bottom_toolbar` via prompt_toolkit | PASS | — |
| B-09 | Ctrl+C interrupt | sets flag, cancels task | PASS | — |
| B-10 | Ctrl+D exit | EOFError handling | PASS | — |
| B-11 | paste preview | NOT IMPLEMENTED | FAIL | Missing |
| B-12 | NO_COLOR | No detection yet | FAIL | Missing |
| B-13 | narrow terminal | No width detection | FAIL | Missing |
| B-14 | model switching | `/model` works | PASS | — |
| B-15 | session switching | `/sessions` works | PASS | — |
| B-16 | tool activity inline | `on_tool` callbacks render cards | PASS | — |
| B-17 | theme/skin system | Hardcoded colors only | FAIL | Missing theme engine |

## Category D — Autonomous Agent Loop

| ID | Feature | ATAR | Status | Gap |
|----|---------|------|--------|-----|
| D-01 | multi-turn loop | `while turn < max_turns` in `agent.py:45` | PASS | — |
| D-02 | tool schemas in request | `_build_body` sends tools | PASS | — |
| D-03 | streaming parser | Accumulates tool_call events | PASS | — |
| D-04 | parallel tool calls | Partial accumulation | PARTIAL | — |
| D-05 | tool results to model | `_messages.append(Message(...))` | PASS | — |
| D-06 | role ordering | Assistant + tool-result messages | PASS | — |
| D-07 | max_iterations | `max_turns=5` | PASS | — |
| D-08 | cancellation | `asyncio.CancelledError` handling | PASS | — |
| D-09 | timeout | Not implemented per-request | FAIL | — |
| D-10 | provider fallback | single provider only | FAIL | — |
| D-11 | fake provider tests | `tests/fake_services/` | PARTIAL | — |

## Category K — Tool Runtime

| ID | Feature | ATAR | Status | Gap |
|----|---------|------|--------|-----|
| K-01 | central registry | `registry.py` with `register()` | PASS | — |
| K-02 | web_search | `web_search.py` via DuckDuckGo | PASS | — |
| K-03 | web_fetch | `web.py` with HTML extraction | PASS | — |
| K-04 | read_file | registered tool | PASS | — |
| K-05 | write_file | registered tool | PASS | — |
| K-06 | terminal | registered tool | PASS | — |
| K-07 | git tools | registered | PASS | — |
| K-08 | test_runner | registered | PASS | — |
| K-09 | approval system | `ToolContext(metadata={"approved":True})` | PARTIAL | No modal UI |
| K-10 | tool timeout | Per-handler timeout | PARTIAL | — |
| K-11 | unknown tool error | Structured error return | PASS | — |
| K-12 | audit events | `secrets.py` has audit | PARTIAL | — |

## Category F — Sessions

| ID | Feature | ATAR | Status | Gap |
|----|---------|------|--------|-----|
| F-01 | session persistence | `SessionManager` with JSON | PASS | — |
| F-02 | session resume | `/sessions` picker loads messages | PASS | — |
| F-03 | tool calls in history | Messages store roles | PARTIAL | Tool calls flattened |
| F-04 | session search | `SessionSearch` FTS | PASS | — |
| F-05 | session title | Titles stored | PASS | — |
