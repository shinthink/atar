<p align="center">
  <img src="https://file.xhunter.icu/uploads/bc8b5d7ba233d134.png" alt="ATAR" width="220">
</p>

<h1 align="center">ATAR</h1>
<p align="center"><strong>Clarity in Complexity.</strong></p>

<p align="center">
  <a href="https://github.com/shinthink/atar/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="../../actions"><img src="https://img.shields.io/badge/tests-34%2F34-brightgreen?style=for-the-badge" alt="Tests"></a>
</p>

---

**A local-first, production-grade terminal AI agent.** ATAR derives its name from *Ataraxia* -- the Greek philosophical concept of tranquility through clarity, composure, and freedom from disturbance. The agent embodies this philosophy: deliberate, composed, and precise in every interaction.

It operates entirely on your machine with your API keys, your files, and your approval. No cloud dependency, no telemetry, no external service requirements beyond the LLM provider you choose.

---

## Architecture

ATAR is built around a clean, layered architecture with strict dependency direction:

```
interfaces (TUI / CLI)
    |
application services (Agent, PlanningEngine, Delegator)
    |
domain/core (EventBus, StateMachine, Protocols)
    |
infrastructure (AnthropicProvider, SqliteSessionStore, DockerBackend)
```

- **Provider-neutral core** -- no vendor SDKs in domain logic
- **Async-native runtime** -- cancellation-aware operations throughout
- **Zero plaintext secrets** -- all credentials resolved from environment
- **Nine packages** with enforced boundary direction

---

## Features

<table>
<tr><td><b>Full-screen terminal interface</b></td><td>23 screens via Textual framework. Chat, plan, tasks, files, terminal, sessions, memory, agents, search, diff, browser, skills, plugins, checkpoints, approvals, audit, settings, diagnostics -- all navigable via sidebar or Ctrl+K command palette.</td></tr>
<tr><td><b>Structured planning with approval gates</b></td><td>AI-generated plans with risk classification (LOW/MEDIUM/HIGH/CRITICAL). High-risk tasks require explicit approval before execution. Editable task dependency graphs.</td></tr>
<tr><td><b>Six built-in tools with runtime enforcement</b></td><td>read_file, write_file, terminal, git, run_tests, web_fetch. Destructive tools blocked without approved=true context. All executions logged with correlation IDs.</td></tr>
<tr><td><b>Persistent memory and session search</b></td><td>Save, recall, and forget facts across sessions. FTS5 full-text search over all conversations via SQLite. JSON persistence with SQLite dual-write for reliability.</td></tr>
<tr><td><b>Governed skill and plugin system</b></td><td>Skills follow a propose/review/activate lifecycle. Plugin hooks with priority ordering, timeout enforcement, and failure isolation per hook.</td></tr>
<tr><td><b>Multi-agent with isolated delegation</b></td><td>Ephemeral subagents with independent context. Parallel task execution. Durable task board tracking queued, running, and completed work.</td></tr>
<tr><td><b>Checkpoint and rollback</b></td><td>Save file state before destructive operations. Restore from checkpoint on failure. List and manage checkpoint history.</td></tr>
<tr><td><b>Batch processing and evaluation</b></td><td>Run multiple prompts in parallel. JSONL trajectory logging with scoring and statistics for benchmark tracking.</td></tr>
<tr><td><b>Docker sandbox with automatic fallback</b></td><td>Rootless container execution when Docker is available. Automatic fallback to local execution when Docker is absent. Verified with real container tests.</td></tr>
<tr><td><b>MCP (Model Context Protocol) connector</b></td><td>JSON-RPC over stdio for MCP-compatible servers. Tool discovery and invocation. Verified with real MCP test server.</td></tr>
<tr><td><b>DeepSeek Integration</b></td><td>Primary provider via Anthropic-compatible endpoint. SSE streaming with thinking block handling. Tool use parsing for structured function calling.</td></tr>
<tr><td><b>Audit trail with correlation IDs</b></td><td>Every tool execution, state transition, and provider call tracked with unique correlation identifiers. Secrets redacted before storage.</td></tr>
</table>

---

## Quick Start

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
git clone https://github.com/shinthink/atar.git
cd atar/ATAR-Project
uv sync
```

### Configuration

Set your API key. ATAR resolves credentials from environment variables automatically:

```bash
export DEEPSEEK_API_KEY="sk-..."
# or
export ANTHROPIC_API_KEY="sk-ant-..."
```

No plaintext keys in config files. No keys in code.

### Usage

```bash
# Start chatting
uv run atar chat "Explain the concept of Ataraxia"

# Resume a session
uv run atar chat --session <id> "Continue our discussion"

# Generate a structured plan with risk classification
uv run atar plan "Build a REST API with rate limiting"

# Auto-approve and execute
uv run atar plan --yes "Add dark mode toggle"

# Analyze code
uv run atar code "Find SQL injection vulnerabilities"

# Delegate to a subagent
uv run atar delegate "Research OAuth 2.0 best practices"

# Parallel delegation
uv run atar delegate-parallel "Capital of France?" "Largest planet?"

# Run batch prompts
uv run atar batch "What is 2+2?" "Capital of Japan?"

# Save a fact to memory
uv run atar remember "project_name" "ATAR Terminal"

# Recall facts
uv run atar recall "project"

# Create a skill
uv run atar skill-propose "concise" "Respond in 1-2 sentences"

# Activate a skill
uv run atar skill-activate "concise"

# Launch the full-screen TUI
uv run atar tui
```

---

## Full Command Reference

| Command | Description |
|---------|-------------|
| `atar chat "prompt"` | Chat with ATAR |
| `atar chat --session <id> "prompt"` | Resume a previous session |
| `atar plan "goal"` | Generate structured plan with risk levels |
| `atar plan --yes "goal"` | Auto-approve plan |
| `atar code "question"` | Analyze codebase with tool access |
| `atar search "query"` | Full-text search across sessions |
| `atar remember <key> <value>` | Save fact to persistent memory |
| `atar recall [query]` | Search or list memory facts |
| `atar forget <key>` | Remove a memory fact |
| `atar skill-propose <name> <prompt>` | Propose a new skill |
| `atar skill-review <name>` | Review a proposed skill |
| `atar skill-activate <name>` | Activate a reviewed skill |
| `atar skill-list` | List all skills with status |
| `atar delegate "task"` | Delegate to subagent |
| `atar delegate --role <role> "task"` | Delegate with specific agent role |
| `atar delegate-parallel "A" "B"` | Run tasks in parallel |
| `atar board-status` | Show task board state |
| `atar batch "A" "B"` | Run multiple prompts |
| `atar eval-log "prompt" --expected "answer"` | Log evaluation run |
| `atar eval-stats` | Show evaluation statistics |
| `atar checkpoint-save <file>` | Save file checkpoint |
| `atar checkpoint-restore <id>` | Restore from checkpoint |
| `atar checkpoint-list` | List all checkpoints |
| `atar tui` | Launch full-screen TUI |
| `atar init` | Initialize ATAR in current directory |

---

## Repository Structure

```
ATAR-Project/
  apps/
    atar-cli/              Typer CLI (22 commands)
    atar-tui/              Textual TUI (23 screens)
  packages/
    atar-core/             Agent, event bus, state machine, planning
    atar-models/           Pydantic data models
    atar-protocols/        Abstract interfaces
    atar-storage/          SQLite + FTS5 persistence
    atar-security/         Secrets manager, audit logging
    atar-tools/            Registry and 6 tool implementations
  providers/
    atar-provider-anthropic/   Anthropic Messages API adapter
  tests/                   Contract and integration tests
  docs/                    ADRs, research, threat model, runbooks
```

---

## Tests

```bash
uv run pytest tests/ -v
# 34 tests in 5 suites:
#   - Event bus (6)
#   - Provider contract (7)
#   - State machine (8)
#   - Tools (9)
#   - Agent integration (4)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/adr/` | Architecture Decision Records (4) |
| `docs/research/` | Documentation Research Gates (8 files) |
| `docs/threat-model/THREAT_MODEL.md` | Threat model with 5 documented entries |
| `docs/runbooks/operations.md` | Backup, restore, upgrade, rollback |
| `docs/project/AUDIT_REPORT.md` | Initial audit (14 findings, all resolved) |
| `docs/project/DEFINITIVE_FINAL_AUDIT.md` | v0.3.0 definitive audit |
| `docs/project/CLOSURE_AUDIT.md` | Closure audit -- 0 findings |
| `CHANGELOG.md` | Full release history (v0.1.0 through v0.3.1) |

---

## Philosophy

The name **ATAR** derives from *Ataraxia* (Greek: ἀταραξία), the Stoic ideal of lucid tranquility -- a state of mind characterized by freedom from distress and worry. This philosophy shapes the agent's design:

- **Clarity before action.** No execution without understanding.
- **Evidence before completion.** Completion requires proof, not model claims.
- **Control before autonomy.** User retains authority over agents.
- **Recovery before confidence.** Every operation is checkpointed and reversible.

ATAR does not panic. It does not rush. It acts with precision and composure.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
