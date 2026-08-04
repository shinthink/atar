<p align="center">
  <img src="atar-logo.png" alt="ATAR Logo" width="200">
</p>

# ATAR

> *Clarity in Complexity.*

ATAR is an autonomous terminal AI agent — a classic REPL with real-time tool execution, streaming responses, and persistent sessions. Inspired by the Stoic concept of **Ataraxia** (tranquility of mind), ATAR operates with calm precision.

Version **v0.8.0** — 401 tests, 65% coverage, 0 ruff, 23/23 audit findings resolved.

## Features

- **Autonomous agent loop** — multi-turn tool calling with narration detection and auto-nudge
- **Hermes-style REPL** — streaming Markdown responses, tool progress cards, slash-command autocomplete (20 commands)
- **Live status bar** — model, token usage, context bar, response time, session timer
- **6 providers** — DeepSeek, OpenAI, Anthropic, OpenRouter, Z.AI, Custom (all with real clients)
- **Memory system** — SQLite-backed, secret-filtered, LLM auto-extraction
- **Session persistence** — save/resume, FTS5 search across history
- **Skills** — auto-created from sessions, registry with pending approval
- **Scheduler** — persistent cron jobs with enable/disable, failure tracking
- **Setup wizard** — interactive first-run configuration (`atar setup`)
- **Checkpoints** — pre-mutation file snapshots, undo/retry, restore
- **Approval flow** — 5-choice interactive approval with diff preview
- **Command validation** — blocks dangerous shell patterns (chaining, substitution, system writes)
- **Memory nudge** — proactive review prompts, stale detection, prune suggestions
- **Skill self-improvement** — usage tracking, success/failure stats, auto-suggestions
- **Context compression** — non-recursive, token-efficient
- **Theme engine** — atar, monochrome, high-contrast skins
- **Plugin system** — auto-discovery across 5 categories
- **Telegram gateway** — bot with allowlist security

## Quick Start

```bash
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync
export DEEPSEEK_API_KEY="your-key"
uv run atar
```

## Commands

| Command | Description |
|---------|-------------|
| `/model` | Switch AI model (two-level: provider → model) |
| `/sessions` | Manage and resume sessions |
| `/code` | Coding mode |
| `/chat` | Chat mode |
| `/toolset` | Switch active toolset |
| `/personality` | Switch or list personas |
| `/retry` | Retry last turn |
| `/undo` | Undo last turn |
| `/compress` | Compress conversation context |
| `/usage` | Show session usage stats |
| `/insights` | Cross-session insights |
| `/memory` | Show persistent memories |
| `/remember` | Save a fact to memory |
| `/search` | Search past sessions |
| `/checkpoints` | List file checkpoints |
| `/status` | Show runtime status |
| `/help` | Show all commands |
| `/clear` | Reset conversation |
| `/quit` | Exit ATAR |

## Architecture

```
atar → rich_repl.py → Agent (tool loop) → ProviderRouter → 6 providers → 14 tools → Session/Memory/Skills
```

## Development

```bash
uv sync && uv run ruff check . && uv run pytest tests/ -q
```

## License

Apache 2.0
