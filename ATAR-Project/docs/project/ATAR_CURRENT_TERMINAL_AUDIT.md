# ATAR CURRENT TERMINAL AUDIT

## 1. Current Command Path

```
[project.scripts]
atar = "atar_cli.main:app"       # Typer app, not a main() function
```

- Entry: `apps/atar-cli/src/atar_cli/main.py:18` — `app = typer.Typer(name="atar", invoke_without_command=True)`
- Default callback: `main.py:21-24` — calls `rich_repl.run_repl()`, a Rich+prompt_toolkit REPL
- **NOT a full-screen Textual TUI**
- The actual Textual TUI lives at `atar_tui.app:main()` but is NOT the default

## 2. Current Startup Flow

1. `atar` → Typer dispatches to `default()` callback
2. `default()` imports and calls `rich_repl.run_repl()`
3. `run_repl()` creates `DeepSeekProvider`, `Agent`, prints Rich banner
4. Enters `prompt_toolkit` REPL loop
5. Each turn: `_agent_turn()` → agent.run() with streaming callbacks
6. Output rendered as Rich Markdown with Obsidian-style code panels
7. On exit: prompt_toolkit raises EOFError → "Ataraxic."

**This is NOT a full-screen TUI.** It is a line-oriented REPL.

## 3. Current TUI Framework

- **Framework:** Textual (apps/atar-tui/src/atar_tui/app.py)
- **Screens:** 23 classes, but only 3-4 have real functionality
- **Real screens:** ChatScreen (streaming chat), PlanScreen (AI planning), TerminalScreen (shell), SkillsScreen, CheckpointsScreen, MemoryScreen, SessionsScreen
- **Informational/placeholder screens:** WelcomeScreen, SetupScreen, ProviderScreen, AgentsScreen, DiffScreen, ProcessScreen, BrowserScreen, PluginsScreen, ApprovalsScreen, UsageScreen, AuditScreen, SettingsScreen, DiagnosticsScreen — **all Static-only text, no real backend connection**
- **Keybinding:** Only Ctrl+Q (quit) and Ctrl+K (command palette), no other bindings
- **Sidebar:** Buttons that switch screens via `switch_screen()`

## 4. Current Runtime Integration

- **ChatScreen:** Creates Agent + AnthropicProvider on-demand in `_send()`, real streaming via StreamCallbacks
- **PlanScreen:** Creates PlanningEngine + Agent on-demand
- **TerminalScreen:** Uses subprocess.run directly — **bypasses ATAR's tool runtime**
- **Other screens:** Most read from SessionManager, MemoryEngine, SkillRegistry, Checkpoint — real backend
- **DeepSeekProvider:** Production-ready, OpenAI-compatible endpoint with tool calling
- **AnthropicProvider:** Also production-ready, Anthropic Messages API

**The TUI IS connected to the real agent runtime, but only ~5 of 23 screens are functional.**

## 5. Missing Features (from the 20-phase specification)

| Feature | Status |
|---------|--------|
| Full-screen TUI as default | ❌ REPL is default, TUI requires `atar tui` |
| First-run setup wizard | ❌ Just checks env var, prints error |
| Non-blocking startup | ❌ REPL blocks on first input |
| Input while loading | ❌ REPL blocks entirely |
| Queued messages | ❌ Not implemented |
| Multiline input | ❌ Single-line prompt_toolkit |
| Slash-command autocomplete | ❌ Manual parsing in REPL |
| Modal overlays | ❌ No Textual modals |
| Approval modals | ❌ Text-based y/n in REPL |
| Session switcher | ❌ No session management UI |
| Model picker | ❌ Not implemented |
| Interrupt/redirect | ❌ Not in TUI |
| Pause/resume | ❌ Not implemented |
| Crash recovery | ❌ No recovery mechanism |
| Non-TTY mode | ❌ No isatty() check |
| Usage panel | ❌ Static text only |
| Agent/task observability | ❌ Not implemented |
| Plan DAG visualization | ❌ Static text only |
| Live tool cards | ❌ Rich panels in REPL only |
| Image/attachment paste | ❌ Not implemented |
| Keybindings config | ❌ Not configurable |
| Graceful fallback | ❌ No fallback logic |

## 6. Broken or Placeholder Functionality

- **WelcomeScreen** — static text, not interactive
- **SetupScreen** — shows env var status, no wizard
- **ProviderScreen** — hardcoded text
- **AgentsScreen** — static description
- **SearchScreen** — searches sessions but doesn't show results well
- **DiffScreen** — static instruction text
- **ProcessScreen** — static description
- **BrowserScreen** — static text
- **PluginsScreen** — static description
- **ApprovalsScreen** — static text
- **UsageScreen** — static text
- **AuditScreen** — static text
- **SettingsScreen** — static paths
- **DiagnosticsScreen** — reads sys.version, os.getcwd

## 7. Architectural Risks

1. **Two disconnected interfaces:** Rich REPL (`rich_repl.run_repl()`) and Textual TUI (`atar_tui.app.main()`) are completely separate codebases with no shared components
2. **REPL bypasses TUI:** Default `atar` goes to REPL, bypassing the 23-screen TUI entirely
3. **No shared command registry:** REPL commands (/code, /chat, /help) are manually parsed strings; TUI has no command system
4. **Inconsistent tool access:** REPL uses bare execute(), TUI TerminalScreen uses subprocess.run directly
5. **No permission engine:** Approval is hardcoded in REPL with y/n prompt
6. **No typed event system for TUI:** TUI screens manually call agent/registry instead of dispatching typed commands

## 8. Exact Files That Need Changes

| File | Issue |
|------|-------|
| `apps/atar-cli/src/atar_cli/main.py:21-24` | Default callback must launch TUI, not REPL |
| `apps/atar-cli/src/atar_cli/rich_repl.py` | Entire file — merge into TUI or remove |
| `apps/atar-tui/src/atar_tui/app.py` | 16 placeholder screens need real backends |
| `pyproject.toml:scripts` | Entry point must point to TUI by default |
| `packages/atar-core/src/atar_core/agent.py` | Agent state machine needs interrupt/redirect |
| `packages/atar-core/src/atar_core/session.py` | Session needs switching without new agent |
| `packages/atar-tools/src/atar_tools/registry.py` | Tools need typed events for TUI streaming |

## 9. Comparison with Hermes Interaction Baseline

| Hermes Feature | ATAR Equivalent | Status |
|---------------|-----------------|--------|
| Conversation-centered TUI | Rich REPL (not TUI) | ❌ Wrong type |
| Instant first frame | Rich Panel banner | ✅ Works |
| Non-blocking init | Not implemented | ❌ |
| Streaming output | Real SSE streaming | ✅ |
| Streaming tool activity | Obsidian panels in REPL | ✅ Works |
| Session persistence | JSON files | ✅ |
| Session switching | Not implemented | ❌ |
| Model/provider selection | Not implemented | ❌ |
| Slash-command autocomplete | Not implemented | ❌ |
| Multiline input | Not implemented | ❌ |
| Interrupt/redirect | Not implemented | ❌ |
| Modal approvals | Not implemented | ❌ |
| Usage/context details | Static text only | ❌ Placeholder |
| Tools/skills/MCP visibility | Banner lists tools | ⚠ Partial |
| Keyboard-first navigation | TUI has sidebar buttons | ⚠ Partial |
| Responsive resizing | Textual handles this | ✅ |
| Graceful non-TTY | Not implemented | ❌ |

## 10. Root Cause of Existing Behavior

ATAR was built incrementally with the CLI as the primary interface. The TUI was added later as a separate module. The `atar` entry point was never migrated to the TUI. The REPL was created as a quick way to get interactive chat without the TUI framework complexity. Now both exist independently, neither satisfying the full specification.

**The `atar` command currently:**
1. Creates a Rich REPL with prompt_toolkit input
2. Has no TTY detection
3. Has no first-run setup
4. Has no modal overlays
5. Has no session management UI
6. Has no slash-command system
7. The Textual TUI exists but requires `atar tui` and is mostly placeholder screens
