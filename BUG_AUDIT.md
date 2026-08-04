# ATAR Bug Audit — 2026-08-04

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 5 |

---

### CRITICAL

#### B01 — Empty tool args silently dropped
**File:** `packages/atar-core/src/atar_core/agent.py:115`  
`if not name or not inp:` — `inp` defaults to `{}` via `args.get("input") or {}`. Empty dict is falsy in Python, so any tool call with no arguments is silently skipped. A tool like `delegate_task({"goal": "test"})` is safe, but any hypothetical tool with truly empty args would be dropped.

**Fix:** Change to `if not name:` only.

---

### HIGH

#### B02 — Early return drops remaining tool calls
**File:** `packages/atar-core/src/atar_core/agent.py:123-126`  
In the tool execution loop, if `too_many_repeated()` fires or `tools_remaining() <= 0`, the entire agent run is terminated with `return`, silently dropping all remaining tool calls in the current turn without executing them or adding error messages.

**Fix:** Use `continue` or `break` with error feedback instead of `return`.

#### B03 — NoneType crash in background memory extraction
**File:** `packages/atar-core/src/atar_core/agent.py:326, 385`  
`get_provider(bg_provider_id)` returns `ProviderProfile | None`. If the provider ID is invalid (returns None), `bg_provider.stream()` crashes with `AttributeError`. Same issue in `_maybe_create_skill` at line 385.

**Fix:** Add None check before calling `.stream()`.

---

### MEDIUM

#### B04 — Duplicate narration pattern computation
**File:** `packages/atar-core/src/atar_core/agent.py:101-108, 175-181`  
The `_narration_patterns` list and `_narration_re` regex are computed twice with identical code. Wasteful and prone to divergence.

**Fix:** Compute once, use in both branches.

#### B05 — Misleading checkpoint comment
**File:** `packages/atar-core/src/atar_core/agent.py:246`  
Comment says "# Save checkpoint before destructive operations" but no checkpoint is actually saved in `_execute_tool`.

**Fix:** Remove misleading comment.

#### B06 — FTS5 search silently swallows all errors
**File:** `packages/atar-storage/src/atar_storage/sqlite_store.py:98-99`  
`except Exception: return []` catches ALL exceptions including bugs, not just FTS5 syntax errors.

**Fix:** Catch only `OperationalError` or log the error.

---

### LOW

#### B07 — Outdated User-Agent
**File:** `packages/atar-tools/src/atar_tools/tools/web.py:68`  
`"ATAR/0.1 (web-research)"` — should be `"ATAR/0.7"`.

#### B08 — Memory file name mismatch
**File:** `packages/atar-core/src/atar_core/paths.py:55-57`  
`atar_memory_file()` returns `memory.json` but actual memory storage is `memory.db` (SQLite).

#### B09 — `os.makedirs` mode may not apply
**File:** `apps/atar-cli/src/atar_cli/setup_wizard.py:73`  
`os.makedirs(..., mode=0o700)` doesn't always apply mode to the leaf directory on some systems. The parent directories get the mode, but the leaf may not.

#### B10 — FTS5 index sync gap
**File:** `packages/atar-storage/src/atar_storage/sqlite_store.py:62-70`  
FTS5 sync is done in a separate session after the main save. If the FTS5 sync fails, session data is saved but unsearchable.

#### B11 — No max_output enforcement in file read
**File:** `packages/atar-tools/src/atar_tools/tools/file.py:46-49`  
`_read_file` reads entire file content with no size limit. Could OOM on large files.
