# ATAR Source Audit — Uploaded Repository

**Audited source:** `atar.zip` → `ATAR-Project/`  
**Audit date:** 2026-08-02  
**Scope:** packaging, CLI/REPL, agent loop, providers, tools, sessions, events, security, and tests.

## Executive conclusion

The repository is a useful early prototype, but it is **not yet equivalent to autonomous agent runtime's autonomous runtime** and is not production-safe.

The current implementation has:

- a real `atar` console entry point;
- a prompt-toolkit/Rich classic REPL;
- a basic iterative tool loop;
- a central tool registry;
- basic DeepSeek and Anthropic HTTP adapters;
- several deterministic fake-provider tests.

However, several features shown in the interface and README are not connected to real runtime behavior. The most serious issues are:

1. all tools are silently auto-approved;
2. file and terminal tools are effectively unrestricted;
3. provider tool-message history is malformed;
4. Anthropic streamed tool calls cannot be reconstructed;
5. four advertised providers are only aliases of the DeepSeek adapter;
6. the default REPL does not persist its current conversation;
7. runtime events/state are not connected to the REPL;
8. clean installation fails because the workspace is invalid;
9. tests pass while failing to verify the most important protocol invariants.

The correct current label is:

```text
ATAR pre-alpha prototype with partial single-agent tool execution
```

not:

```text
production-ready autonomous agent
```

---

# 1. What currently works

## Console entry point

`pyproject.toml` registers:

```toml
[project.scripts]
atar = "atar_cli.main:app"
```

`apps/atar-cli/src/atar_cli/main.py` routes bare interactive `atar` to `run_repl()` and `--tui` to the Textual application.

## Classic REPL foundation

`apps/atar-cli/src/atar_cli/rich_repl.py` uses:

- `prompt_toolkit.PromptSession`;
- Rich `Console`, `Panel`, `Markdown`, and `Rule`;
- a compact prompt;
- a status toolbar;
- slash-command-like handlers;
- inline tool callbacks.

This is the right general direction for a shell-native ATAR interface.

## Basic iterative loop

`packages/atar-core/src/atar_core/agent.py` can:

1. call a provider;
2. detect a tool-call event;
3. execute a registered tool;
4. call the model again;
5. return final text.

The concept is correct, but its message protocol and security model are not yet correct.

## Central registry foundation

`packages/atar-tools/src/atar_tools/registry.py` provides:

- registration;
- lookup;
- toolsets;
- schema conversion;
- execution;
- result truncation;
- basic approval flag;
- audit call.

It needs major hardening but is a valid foundation.

## Existing tests

With a manually constructed `PYTHONPATH`, the current contract and integration subset produced:

```text
44 passed in 1.17s
```

This proves some internal components are importable and the fake-provider happy paths run. It does **not** prove provider correctness, security, packaging, or true feature parity.

---

# 2. P0 security findings

## P0-01 — Approval is bypassed for every agent tool

**File:** `packages/atar-core/src/atar_core/agent.py`  
**Lines:** approximately 124–128

```python
ctx = ToolContext(metadata={"approved": True})
```

Every model-selected tool is executed as already approved.

Consequences:

- `write_file` approval is bypassed;
- `terminal` approval is bypassed;
- destructive commands can run without user consent;
- future tools inherit the same bypass;
- scheduler, subagents, and batch mode would inherit unsafe behavior if they reuse this path.

Required fix:

- introduce an `ApprovalCoordinator`;
- use tool risk, capability, path, network target, and operation;
- no hardcoded approval;
- support reject, approve once, and narrowly scoped approval;
- persist approval evidence;
- ensure child agents cannot escalate.

## P0-02 — File tools allow arbitrary host paths

**File:** `packages/atar-tools/src/atar_tools/tools/file.py`  
**Lines:** approximately 13–46

The tool accepts absolute paths and does not prevent:

- `../` traversal;
- symlink escape;
- reads outside workspace;
- writes outside workspace;
- access to SSH keys, shell config, cloud credentials, or system files.

Required fix:

- resolve with `Path.resolve(strict=False)`;
- enforce an approved workspace root;
- reject paths outside allowed roots;
- check symlink traversal;
- protect sensitive paths;
- separate read and write capabilities;
- create checkpoint before mutation;
- add negative tests.

## P0-03 — Terminal tool is unrestricted and auto-approved

**File:** `packages/atar-tools/src/atar_tools/tools/terminal.py`  
**Lines:** approximately 13–46

It uses:

```python
asyncio.create_subprocess_shell(command)
```

without:

- dangerous-command classification;
- sandbox enforcement;
- environment filtering;
- workspace restriction;
- network policy;
- process-tree cancellation;
- output redaction.

The timeout path does not explicitly terminate the process tree.

Required fix:

- default to sandbox/restricted execution;
- classify command risk;
- inspect shell metacharacters and targets;
- require approval for sensitive operations;
- scrub environment;
- terminate process group on timeout/cancel;
- add resource limits;
- record exit code and evidence;
- block known catastrophic commands.

## P0-04 — Plaintext API-key fallback

**File:** `packages/atar-security/src/atar_security/secrets.py`  
**Lines:** approximately 35–69

When keyring is unavailable, API keys are written directly to:

```text
~/.atar/config.json
```

The comment says “encrypted in production,” but no encryption exists and file mode is not hardened.

Required fix:

- keyring-first remains;
- fallback must be explicit and visibly insecure, or use an encrypted store;
- never silently store plaintext;
- enforce restrictive file permissions;
- add secret redaction tests;
- never persist keys in project-local `.atar`.

## P0-05 — Cross-provider key confusion

`get_api_key("deepseek")` accepts both:

```text
DEEPSEEK_API_KEY
ANTHROPIC_API_KEY
```

`AnthropicProvider` also resolves `DEEPSEEK_API_KEY`.

This can send the wrong provider's credential to the wrong endpoint.

Required fix:

- each provider resolves only its own credential aliases;
- a compatibility endpoint must have its own explicit profile;
- never infer that an Anthropic key is a DeepSeek key or vice versa;
- add endpoint/credential binding tests.

## P0-06 — Audit log does not redact arguments

**File:** `packages/atar-tools/src/atar_tools/registry.py`  
**Around line:** 83

```python
log_action(f"tool:{name}", args=str(args)[:200], ...)
```

Commands, file content, URLs, tokens, or secrets may enter logs.

Required fix:

- central structured redactor;
- field-aware redaction;
- prohibit raw file content and authorization data;
- test common secret formats.

## P0-07 — Web tools lack SSRF controls

`web_fetch` accepts arbitrary URLs and can potentially access:

- localhost;
- private network ranges;
- cloud metadata endpoints;
- internal services;
- non-HTTP schemes if future parsing changes.

Required fix:

- scheme allowlist;
- DNS/IP resolution checks;
- private/link-local/loopback blocking by default;
- redirect revalidation;
- response-size limits;
- content-type handling;
- explicit internal-network capability.

---

# 3. P1 autonomous-runtime findings

## P1-01 — Tool message history is malformed

**File:** `packages/atar-core/src/atar_core/agent.py`  
**Around lines:** 70–91

After a tool call, ATAR appends:

```python
Message(
    role="user",
    content=f"Tool {name} result: {result.output}",
)
```

It does not append:

1. the assistant message containing structured tool calls;
2. a `tool` role message;
3. `tool_call_id`;
4. structured error/result metadata.

Observed manual probe:

```text
roles = ['user', 'user', 'assistant']
```

Correct internal sequence should be equivalent to:

```text
system
user
assistant(tool_calls=[...])
tool(tool_call_id=...)
assistant(final)
```

This is a core reason ATAR cannot be reliably provider-neutral.

## P1-02 — Tool errors are hidden from the model

The agent sends only:

```python
result.output
```

When a tool returns `success=False` and sets `error`, the model may receive an empty string.

Required fix:

- normalized tool-result envelope;
- include success, error code, retryability, metadata, and evidence;
- always return a meaningful structured result to the model.

## P1-03 — Anthropic streamed tool calls are not reconstructed

**File:** `providers/atar-provider-anthropic/.../client.py`  
**Around lines:** 134–160

Observed event sequence:

```text
tool_call {'id': 'toolu_1', 'name': 'web_search', 'partial': True}
tool_call {'partial_json': '{"query":"ataraxia"}', 'partial': True}
tool_call {'partial': False}
```

The agent skips partial calls. The final event contains no ID, name, or parsed input. Therefore a normal Anthropic streaming `tool_use` block cannot execute.

Required fix:

- stateful accumulator keyed by content-block index;
- accumulate ID, name, and partial JSON;
- emit exactly one complete normalized tool call on block stop;
- support multiple blocks;
- malformed JSON must become a structured recoverable error.

## P1-04 — DeepSeek parser supports only one tool call

**File:** `providers/atar-provider-deepseek/.../client.py`  
**Around lines:** 72–108

It reads only:

```python
tc[0]
```

and keeps one global:

```text
tool_id
tool_name
tool_args
```

It cannot correctly support:

- multiple parallel calls;
- fragmented calls by index;
- several calls in one assistant response;
- independent JSON accumulators.

Required fix:

- accumulator per tool-call index/ID;
- emit calls in original order;
- test interleaved fragments;
- preserve finish reason and usage.

## P1-05 — Advertised provider support is mostly non-functional

The OpenAI, OpenRouter, Z.AI, and Custom clients are very small subclasses of `DeepSeekProvider` without provider-specific defaults.

They inherit DeepSeek defaults such as:

```text
base URL: https://api.deepseek.com/v1
model: deepseek-chat
environment key: DEEPSEEK_API_KEY
```

They also all expose a class named `OpenAiProvider`.

`create_router()` only builds:

- DeepSeek;
- Anthropic.

It does not instantiate OpenAI, OpenRouter, Z.AI, or Custom.

Therefore README's “6 providers” claim is not currently true.

Required fix:

- real adapter/profile per provider;
- correct class names;
- correct base URL, key, headers, mode, model discovery;
- provider registry;
- configuration-driven router;
- contract tests for each adapter;
- do not hardcode current model names permanently.

## P1-06 — `/model` is mostly cosmetic

`rich_repl.py` writes selected provider/model to config, but `create_router()` ignores that selection and constructs fixed DeepSeek/Anthropic instances with fixed models.

Required fix:

- normalized provider profile;
- router reads selected provider/model;
- UI displays actual active provider/model;
- connection/capability check after switching;
- test that requests really go to the selected adapter.

## P1-07 — Default REPL does not persist its active conversation

`run_repl()` generates a random display session ID but does not create/save a `Session` for each turn.

`_try_resume_session()` exists but is unused.

`/sessions` can load previously stored sessions, but the current REPL session is not saved through the normal turn path.

Consequences:

- “persistent sessions” claim is inaccurate;
- current conversation disappears after exit;
- tool calls/results are not stored;
- resumed context cannot be correct.

Required fix:

- create/resume a real session before showing banner;
- persist each structured message and runtime state;
- save after model/tool steps, not only at final exit;
- structured tool messages in database;
- crash-safe writes.

## P1-08 — State machine and event bus are disconnected

`Agent` has both:

```python
event_bus: EventBus
state: AgentStateMachine
```

but the default state machine is not constructed with the agent's event bus.

The agent mostly transitions:

```text
IDLE → UNDERSTANDING → COMPLETED
```

It does not transition through tool execution, approval, verification, or repair states.

If the event bus were connected, `state_machine.py` attempts to construct values such as:

```text
EventType("state_understanding")
```

but those enum values are not defined.

Required fix:

- one injected event bus;
- valid typed state events;
- full runtime transitions;
- REPL subscribes to events instead of callbacks/string assumptions;
- event tests against real agent turns.

## P1-09 — REPL tool display is static and inaccurate

The REPL imports and registers only:

```text
read_file
write_file
terminal
web_fetch
web_search
```

Manual registry probe returned exactly those five tools.

The banner claims:

```text
git
run_tests
patch
search_files
browser
execute_code
cronjob
delegate_task
7 tools
7 skills
```

These claims are hardcoded and do not reflect registry availability.

Required fix:

- discover tools centrally;
- banner reads actual registry/toolset state;
- availability checks;
- never display unregistered tools;
- never hardcode tool/skill counts.

## P1-10 — System prompt encourages unsafe coding

`BASE_PROMPT` says:

```text
For coding — call write_file IMMEDIATELY.
```

This conflicts with safe autonomous coding.

Correct behavior:

```text
inspect
→ understand
→ plan when non-trivial
→ checkpoint
→ patch
→ test
→ verify
```

Required fix:

- remove immediate-write instruction;
- include evidence and no-fabrication policy;
- provider-neutral prompt builder;
- stable prompt prefix;
- project context and security layer.

## P1-11 — REPL is not truly non-blocking

During `_agent_turn`, the REPL awaits the active task before showing the next prompt.

It therefore lacks true:

- queued messages;
- steering;
- background prompts;
- non-blocking input;
- reliable interrupt-and-redirect.

The response text is not streamed into the transcript. Tokens only update a spinner preview and are rendered as one final panel.

Required fix:

- coordinated output queue;
- prompt remains active while agent runs, or explicit foreground/background state;
- `patch_stdout`;
- real text streaming;
- queue/steer contracts;
- robust Ctrl+C cancellation.

## P1-12 — Status data is estimated or hardcoded

The status bar uses:

- fixed 128K context;
- estimated tokens from characters/turns;
- no real cost;
- static model assumptions.

Required fix:

- provider usage metadata;
- actual model capability catalog;
- visibly mark estimates;
- never present estimates as authoritative.

---

# 4. P1 packaging and release findings

## P1-13 — `uv sync` fails

The workspace declares:

```text
packages/atar-planning
```

but that directory has no `pyproject.toml`.

Observed:

```text
Workspace member .../packages/atar-planning is missing a pyproject.toml
```

This blocks a clean installation.

Required fix:

- add a valid package manifest or remove the member;
- verify every workspace glob;
- run clean install from an empty environment.

## P1-14 — Archived `.venv` is machine-specific

The uploaded `.venv` points to a Python installation path from the originating machine and fails with:

```text
ModuleNotFoundError: No module named 'encodings'
```

A virtual environment must never be distributed as part of source.

The archive also contains:

```text
.venv        ~430 MB
.mypy_cache
.pytest_cache
.ruff_cache
.atar/sessions.db
.atar/sessions.json
.atar/memory.json
```

Required fix:

- root `.gitignore`;
- exclude local user state, databases, memory, checkpoints, caches, and venv;
- clean release archives;
- data-export feature separate from source distribution.

## P1-15 — Version and license are inconsistent

Examples:

```text
pyproject version: 0.1.0
REPL banner: ATAR v0.6.0
pyproject license: MIT
README license: Apache 2.0
no root LICENSE file observed
```

Required fix:

- single source of version;
- import package version dynamically;
- choose and include one license;
- release checks reject inconsistencies.

---

# 5. Test-quality findings

## Current result

The current contract/integration subset passes:

```text
44 passed
```

but several tests are too permissive.

## Weak role-ordering test

The current test only verifies that `"user"` and `"assistant"` exist. It does not require:

```text
assistant(tool_calls)
→ tool(tool_call_id)
→ assistant(final)
```

Therefore malformed `user → user → assistant` passes.

## Weak PTY test

A test named like bare-ATAR startup actually executes:

```text
atar --help
```

It does not verify that bare `atar` opens the intended REPL.

## Timeout accepted as success

The non-interactive test accepts exit code:

```text
124
```

which is `timeout` and may mean the program hung.

## Provider tests only cover fake provider

No deterministic compliance suite exercises:

- DeepSeek stream fragments;
- Anthropic content blocks;
- multiple tool calls;
- malformed JSON;
- real adapter defaults;
- selected provider routing.

Required test names include:

```text
test_tool_history_uses_assistant_and_tool_roles
test_tool_result_keeps_tool_call_id
test_tool_error_returns_to_model
test_anthropic_stream_accumulates_tool_use
test_deepseek_stream_accumulates_multiple_calls
test_parallel_tool_results_preserve_call_order
test_openai_profile_uses_openai_endpoint_and_key
test_openrouter_profile_uses_openrouter_endpoint_and_key
test_zai_profile_uses_zai_endpoint_and_key
test_custom_profile_requires_explicit_base_url
test_model_switch_changes_actual_provider_request
test_repl_session_persists_every_step
test_agent_does_not_auto_approve_write
test_path_traversal_is_blocked
test_symlink_escape_is_blocked
test_terminal_timeout_kills_process_tree
test_bare_atar_opens_repl_in_pty
test_non_tty_never_accepts_timeout_as_success
test_clean_uv_sync
```

---

# 6. Recommended remediation order

## Phase 0 — Stop unsafe execution

1. remove hardcoded `approved=True`;
2. restrict file paths;
3. restrict/sandbox terminal;
4. redact logs;
5. block SSRF;
6. fix secret storage;
7. add negative tests.

## Phase 1 — Correct provider-neutral message protocol

1. typed assistant tool-call message;
2. typed tool result message;
3. `tool_call_id`;
4. provider adapters translate to/from normalized messages;
5. errors returned to model;
6. strict history invariants.

## Phase 2 — Correct streaming adapters

1. DeepSeek/OpenAI-compatible per-call accumulator;
2. Anthropic content-block accumulator;
3. parallel calls;
4. malformed JSON;
5. finish reason and usage.

## Phase 3 — Real provider registry/router

1. provider profiles;
2. actual OpenAI/Anthropic/DeepSeek/Z.AI/OpenRouter/Custom adapters;
3. API-key-only setup for built-ins;
4. model discovery;
5. capability reports;
6. correct switch/fallback behavior.

## Phase 4 — Sessions and event-driven runtime

1. structured session schema;
2. persistence during each step;
3. event bus injection;
4. complete state transitions;
5. crash recovery;
6. REPL consumes typed events.

## Phase 5 — Real production-quality REPL

1. dynamic tool/skill banner;
2. true streaming output;
3. multiline and completion;
4. queue/steer/background;
5. real status data;
6. PTY tests;
7. width/NO_COLOR tests.

## Phase 6 — Packaging and clean-install

1. repair workspace;
2. add root `.gitignore`;
3. remove local state from source archives;
4. unify version/license;
5. clean install/upgrade test.

## Phase 7 — Parity audit

Only after P0/P1 are fixed, run the full feature parity audit prompt and classify every feature with evidence.

---

# 7. Release recommendation

**Do not publish ATAR as production-ready or production-ready yet.**

Recommended public label:

```text
ATAR 0.1 pre-alpha
```

Minimum release gate for an autonomous-agent alpha:

```text
[ ] no implicit tool approval
[ ] workspace-safe file tools
[ ] sandboxed/approved terminal
[ ] correct assistant/tool message protocol
[ ] DeepSeek and Anthropic tool-stream contract tests
[ ] session persistence in default REPL
[ ] real runtime events in REPL
[ ] clean uv sync/install
[ ] accurate banner/provider/tool claims
[ ] P0 security tests pass
```
