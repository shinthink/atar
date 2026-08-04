# ATAR CLASSIC REPL AUDIT

## Inspection Results

| Q | Question | Answer | File |
|---|----------|--------|------|
| 1 | Full-screen Textual? | No — Rich REPL | `rich_repl.py` |
| 2 | Alternate-screen mode? | No | `rich_repl.py` |
| 3 | Huge banner/frame? | **YES** — 25-line two-column Panel with outer border | `rich_repl.py:103-133` |
| 4 | Paints terminal bg? | No explicit bg color | OK |
| 5 | Input library? | prompt_toolkit PromptSession | `rich_repl.py:22` |
| 6 | Scrollback preserved? | Yes — no alt screen | OK |
| 7 | Tool events real? | Yes — agent streaming + tool_call callbacks | OK |
| 8 | Concurrent output? | No queue — bare console.print() | GAP |
| 9 | Spinner corrupts text? | No spinner currently | OK |
| 10 | Unicode width? | Unchecked — bare console.print() | GAP |
| 11 | Resize works? | Not tested | UNKNOWN |
| 12 | One renderer? | Yes — single Rich Console | OK |
| 13 | Slash commands centralized? | No — inline if/elif chain | GAP |
| 14 | Ctrl+C interrupts agent? | Only process kill (KeyboardInterrupt in asyncio.run) | GAP |
| 15 | Ctrl+D exits? | Yes — EOFError handling | OK |
| 16 | Paste preview? | **NO** | GAP |
| 17 | Secrets in output? | Not in user output | OK |

## CRITICAL FINDINGS

### F-001: Banner too large
- **File:** `rich_repl.py:103-133`
- **Problem:** 25-line two-column Panel with outer border, inner Panel, 12 add_row() calls, tools list, "--help" line
- **Spec violation:** §8 — banner must be 8-12 lines max, no full-width outer frame
- **Fix:** Replace with compact 6-line logo + metadata only

### F-002: No slash-command registry
- **File:** `rich_repl.py:213-265`
- **Problem:** All commands are inline if/elif, duplicated across code
- **Fix:** Create `commands/registry.py` with centralized Command objects

### F-003: No status bar
- **File:** `rich_repl.py` (entire file)
- **Problem:** No persistent bottom status bar showing model/context/cost
- **Fix:** Add prompt_toolkit bottom toolbar

### F-004: No paste preview
- **File:** `rich_repl.py:173`
- **Problem:** Large pastes flood terminal
- **Fix:** Use prompt_toolkit bracketed paste with preview

### F-005: No Ctrl+C agent interrupt
- **File:** `rich_repl.py:153-175`
- **Problem:** KeyboardInterrupt kills the process, not just the agent
- **Fix:** Wrap agent run with asyncio.CancelledError handling

### F-006: No multiline support
- **File:** `rich_repl.py:173`
- **Problem:** Enter always sends, no Alt+Enter or Shift+Enter for newline
- **Fix:** Configure prompt_toolkit multiline keybindings

### F-007: Direct console.print() from async callbacks
- **File:** `rich_repl.py:166,176-182`
- **Problem:** No output serialization — concurrent tool/streaming events can interleave
- **Fix:** Use Rich Live display or output queue
