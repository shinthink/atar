<p align="center">
<pre>
  :::. :::::::::::::::.    :::::::..         :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::
  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;        ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''
 ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['       ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[
c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c        c$$$cc$$$c"$$c.    "$$ $$""""   $$$ "Y$c$$     $$
 888   888, 88,   888   888,888b "88bo,     888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,
 YMM   ""`  MMM   YMM   ""` MMMM   "W"      YMM   ""`   `'YMUP"YMM""""YUMMMMMM     YM     MMM

Clarity in Complexity.
</pre>
</p>

<h1 align="center">ATAR</h1>

<p align="center">
  <a href="https://github.com/shinthink/atar/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-353%2F353-brightgreen?style=for-the-badge" alt="353/353 Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/coverage-65%25-blue?style=for-the-badge" alt="65% Coverage"></a>
  <a href="#"><img src="https://img.shields.io/badge/RUFF-clean-black?style=for-the-badge&logo=ruff&logoColor=white" alt="RUFF Clean"></a>
</p>

---

<p align="center">
<strong><em>An autonomous AI agent that lives in your terminal.</em></strong>
</p>

ATAR is a local-first, open-source terminal agent designed for developers, researchers, and builders who want AI assistance without sacrificing control. It runs entirely on your machine with your API keys, your files, and your explicit approval. No cloud middleware. No telemetry. No lock-in.

The name derives from **Ataraxia** (ἀταραξία) — the ancient Greek philosophical ideal of a lucid state of robust tranquility, characterized by ongoing freedom from distress and worry. For the Stoics, ataraxia was the natural result of living virtuously in accordance with reason. For the Epicureans, it was the highest form of pleasure — the absence of mental disturbance. For the Pyrrhonian Skeptics, it was achieved by suspending judgment on all non-evident matters.

ATAR embodies this philosophy in software: **calm precision over frantic reactivity. Evidence over assumption. Clarity over confusion.** When you ask it to research, it searches the web, extracts sources, compares claims, and synthesizes answers with citations — never fabricating references. When you ask it to code, it inspects the repository, creates a plan, makes targeted edits, runs your tests, and verifies the results — never claiming completion without proof.

Built with Python 3.12+, prompt_toolkit, Rich, and a clean modular architecture, ATAR supports six AI providers including DeepSeek (with native tool calling), OpenAI, and Anthropic. Its REPL streams responses in real-time, shows live tool execution progress, and keeps a persistent status bar tracking tokens, context usage, and session time — everything you need, nothing you don't.

<strong>ATAR is not a chatbot. It is an autonomous agent that thinks, acts, verifies, and reports — all from the comfort of your terminal.</strong>

---

## Table of Contents

- [Features](#features)
- [Quick Install](#quick-install)
- [Usage](#usage)
- [Slash Commands](#slash-commands)
- [Keybindings](#keybindings)
- [Tools](#tools)
- [Providers](#providers)
- [Architecture](#architecture)
- [Sessions & Memory](#sessions--memory)
- [Themes](#themes)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Features

<table>
<tr><td width="200"><b>Autonomous agent loop</b></td><td>Multi-turn tool calling with streaming. The model decides what to do — ATAR executes, feeds results back, and continues until the task is complete. No one-shot responses.</td></tr>
<tr><td><b>Real terminal interface</b></td><td>prompt_toolkit REPL with slash-command autocomplete, multiline editing, streaming Markdown responses, live tool progress cards (<code>┊ ◌ preparing...</code> → <code>│ ✓ Done (0.3s)</code>), interrupt handling, and a persistent status bar.</td></tr>
<tr><td><b>Live status bar</b></td><td>Model name, token usage, context bar (<code>[████░░░░░░] 20%</code>), tools executed, turns elapsed, response time, session timer. Updates in real time.</td></tr>
<tr><td><b>Six AI providers</b></td><td>DeepSeek (native tool calling), OpenAI, Anthropic, OpenRouter, Z.AI, and Custom OpenAI-compatible endpoints. Switch with <code>/model</code>. Provider fallback on failure.</td></tr>
<tr><td><b>Research tools</b></td><td><code>web_search</code> (DuckDuckGo) and <code>web_fetch</code> for real-time information retrieval. The agent searches, extracts sources, and synthesizes answers with citations.</td></tr>
<tr><td><b>Coding tools</b></td><td>Write files, read files, run terminal commands, git operations, run tests — all from the REPL with approval gates, live output streaming, and proper error handling.</td></tr>
<tr><td><b>Memory system</b></td><td>SQLite-backed persistent memory with secret filtering. LLM auto-extraction captures facts, preferences, and decisions across sessions. Searchable, supersedable, confidence-scored.</td></tr>
<tr><td><b>Session persistence</b></td><td>Save and resume conversations with structured tool-call history. FTS5 full-text search across past sessions. Fresh session or resume previous.</td></tr>
<tr><td><b>Skills system</b></td><td>Auto-created from complex sessions. Pending approval workflow. Skill manager with singleton registry.</td></tr>
<tr><td><b>Scheduler</b></td><td>Persistent cron jobs with enable/disable, failure tracking, and auto-disable after repeated failures.</td></tr>
<tr><td><b>Theme engine</b></td><td>Built-in <code>atar</code>, <code>monochrome</code>, and <code>high-contrast</code> skins. NO_COLOR support. Terminal-width responsive layout.</td></tr>
<tr><td><b>Provider fallback</b></td><td>Automatic failover across providers. If one provider fails, the next takes over — no manual intervention needed.</td></tr>
</table>

---

## Quick Install

### Linux

```bash
# Clone and install
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync

# Set your API key
export DEEPSEEK_API_KEY="your-deepseek-key"

# Launch
uv run atar
```

### macOS

Same as Linux. Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

### Windows (WSL2)

Same as Linux. Run inside WSL2 terminal.

---

## Usage

```bash
atar              # Classic REPL (default)
atar --cli         # Force classic REPL mode
atar --tui         # Full-screen Textual TUI
atar --run "..."   # Single query, non-interactive
atar --help        # Show all commands and flags
atar --version     # Show version
```

On first run, ATAR creates `~/.atar/config.json` for configuration storage. API keys are resolved from: OS keyring → environment variables → config file.

### First Run

```
  :::. :::::::::::::::.    :::::::..         :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::
  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;        ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''
 ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['       ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[
c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c        c$$$cc$$$c"$$c.    "$$ $$""""   $$$ "Y$c$$     $$
 888   888, 88,   888   888,888b "88bo,     888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,
 YMM   ""`  MMM   YMM   ""` MMMM   "W"      YMM   ""`   `'YMUP"YMM""""YUMMMMMM     YM     MMM

Clarity in Complexity.

                                           ╭──────────────────────────────────────────╮
                ####  ####                 │  deepseek-chat · ~/my-project             │
           ####   ##   ##  ####            │  Session: a1b2c3d4                        │
        ###      ##    ###     ###         │                                          │
      ###       ##      ##        ##       │  Available Tools                         │
     ##        ##        ##        ###     │    read_file  write_file  terminal        │
   ###        ##          ##         ##    │    web_search  web_fetch  git  run_tests  │
   ##         #            ##         ##   │                                          │
  ##         ##             ##        ##   │  Skills                                  │
  ##        ##      ##       ##        ##  │    coding  research  file-ops  planning   │
  #        ##      ####      ##        ##  │    multi-agent  memory  security          │
  #######    ######    ###### #######*###  │                                          │
  ##     ##  ######    #####   ##     *#   │  7 tools · 7 skills · /help for commands  │
   #*    #                      ##    ##   │  Tip: Type /model to switch AI            │
   ##   ##                       ##  ##    ╰──────────────────────────────────────────╯
    #####                         ####
      ##                          ##
        ###                    ####        ◆ deepseek-chat │ 0K/128K [░░░░░░░░░░] 0% │ tools 0 │ ✓0s
          ####              ####
              ##############

› halo
──────────────────────────────────────────────────────────────────────────────────

╭──────────────────────────── ATAR ────────────────────────────╮
│  Halo! Ada yang bisa saya bantu?                             │
╰──────────────────────────────────────────────────────────────╯
──────────────────────────────────────────────────────────────────────────────────
›
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/model` | Switch AI model provider (DeepSeek, OpenAI, Anthropic, etc.) |
| `/sessions` | Browse and resume saved sessions |
| `/code` | Enter coding mode with file tools enabled |
| `/chat` | Return to standard chat mode |
| `/toolset` | Switch active toolset (safe, file, terminal, web, research, full) |
| `/personality` | Switch or list AI personas |
| `/retry` | Retry the last turn (in-place regenerate) |
| `/undo` | Undo the last turn (removes user + assistant + tool results) |
| `/compress` | Compress conversation context to free tokens |
| `/usage` | Show current session token and tool usage |
| `/insights` | Show cross-session usage insights |
| `/memory` | Show persistent memories |
| `/remember` | Save a fact to persistent memory |
| `/checkpoints` | List file checkpoints |
| `/help` | Show all available commands |
| `/clear` / `/reset` | Reset conversation and start fresh |
| `/quit` / `/exit` / `/q` | Exit ATAR |

Press `Tab` while typing a slash command to see completions.

---

## Keybindings

| Binding | Action |
|---------|--------|
| `Enter` | Send message |
| `Alt+Enter` | Insert newline (multiline input) |
| `Tab` | Show slash-command completions |
| `Ctrl+C` | Interrupt current agent run, prompt for redirect |
| `Ctrl+C` twice | Force exit |
| `Ctrl+D` | Exit with confirmation |
| `Ctrl+V` | Paste (with preview for large content) |

---

## Tools

ATAR exposes 14 registered tools to the agent. All tools originate from one central registry used by the agent, REPL, and tests:

| Tool | Description | Risk |
|------|-------------|------|
| `read_file` | Read file contents | Read-only |
| `write_file` | Write or overwrite files | Write |
| `terminal` | Execute shell commands | Execute |
| `web_search` | Search the web via DuckDuckGo | Network |
| `web_fetch` | Extract content from URLs | Network |
| `git` | Git operations (status, diff, log) | Read-only |
| `run_tests` | Run test suite | Execute |
| `patch` | Structured file edits | Write |
| `search_files` | Search file contents or names | Read-only |
| `browser` | Browser navigation | Network |
| `execute_code` | Run Python code with tool RPC | Execute |
| `cronjob` | Schedule recurring tasks | Execute |
| `delegate_task` | Spawn subagent for parallel work | Execute |

---

## Providers

ATAR supports six provider families through a unified abstraction:

| Provider | Model | Native Tools | Status |
|----------|-------|-------------|--------|
| **DeepSeek** | deepseek-chat, deepseek-v4-pro | Yes (OpenAI endpoint) | Active |
| **OpenAI** | gpt-4o, gpt-4-turbo | Inherited | Active |
| **Anthropic** | claude-sonnet-4 | Inherited | Active |
| **OpenRouter** | deepseek/deepseek-chat | Inherited | Active |
| **Z.AI** | z-ai models | Inherited | Active |
| **Custom** | Any OpenAI-compatible endpoint | Inherited | Active |

All providers use the OpenAI-compatible chat completions API. DeepSeek's native tool calling is supported through `tool_choice="auto"`.

Provider fallback: if the primary provider fails, ATAR automatically tries the next available provider in the configured chain.

---

## Architecture

```
atar (entry point)
  └── rich_repl.py              prompt_toolkit + Rich REPL
        └── Agent                 multi-turn tool-calling loop
              ├── ProviderRouter   fallback chain across 6 providers
              ├── Tool Registry    14 tools with auto-discovery
              ├── Memory System    SQLite, secret-filtered, auto-extraction
              ├── Session Manager  SQLite persistence + FTS5 search
              ├── Skills Manager   auto-creation, pending approval
              ├── Scheduler        persistent cron + failure tracking
              └── Theme Engine     atar / monochrome / high-contrast
```

ATAR follows a clean monorepo structure:

```
ATAR-Project/
├── apps/
│   ├── atar-cli/         CLI + REPL application
│   └── atar-tui/         Textual TUI application
├── packages/
│   ├── atar-core/        Agent, event bus, state machine
│   ├── atar-models/      Pydantic models
│   ├── atar-protocols/   Interface definitions
│   ├── atar-tools/       Tool implementations + registry
│   ├── atar-storage/     SQLAlchemy + SQLite
│   └── atar-security/    Keyring + audit
├── providers/
│   ├── atar-provider-deepseek/
│   ├── atar-provider-openai/
│   ├── atar-provider-anthropic/
│   ├── atar-provider-openrouter/
│   ├── atar-provider-zai/
│   └── atar-provider-custom/
├── tests/
│   ├── contract/              Protocol + tool contract tests
│   ├── integration/           Agent loop + acceptance tests
│   ├── security/              Security hardening tests
│   └── tui/                   PTY entry point tests
├── plugins/                   Auto-discoverable plugin categories
└── docs/                      Architecture, ADRs, audit reports
```

---

## Sessions & Memory

Sessions persist the full conversation: user messages, assistant responses, tool calls, tool results, token usage, and timestamps. Resume a session with `/sessions`.

- **SQLite storage**: Sessions and memory stored in SQLite with FTS5 full-text search.
- **Fresh session**: Every `atar` launch starts fresh by default.
- **Resume**: Use `/sessions` to pick and resume a previous session.
- **Search**: `/search` for full-text search across past sessions.
- **Memory**: Persistent facts, preferences, and decisions auto-extracted by background LLM.
- **Clear**: `/clear` resets the conversation within a session.

---

## Themes

ATAR ships with three built-in themes:

| Theme | Description |
|-------|-------------|
| `atar` | Default — calm blue palette (#67D8FF primary) |
| `monochrome` | Black and white, activates on NO_COLOR or TERM=dumb |
| `high-contrast` | Cyan/gold/green for accessibility |

Theme colors are applied to: ASCII banner, rule separators, tool progress indicators, response container, status bar, and input prompt.

Custom themes can be loaded from `~/.atar/themes/`.

---

## Environment

```bash
# Required — set your API key
export DEEPSEEK_API_KEY="sk-..."

# Optional — override provider
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Optional — disable color
export NO_COLOR=1
```

ATAR resolves credentials in order: OS keyring → environment variables → `~/.atar/config.json`.

---

## Development

```bash
# Clone and setup
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync

# Lint
uv run ruff check .

# Run all tests (353)
uv run pytest tests/ -q

# Run with coverage (target: 65%)
uv run pytest tests/ --cov=packages --cov=apps -q

# Run specific test suite
uv run pytest tests/integration/test_agent_loop.py -v

# Run ATAR in development
uv run atar
```

### Test Coverage

| Suite | Tests | Description |
|-------|-------|-------------|
| `tests/contract/` | 205 | Provider contracts, tool coverage, core modules, display helpers |
| `tests/integration/` | 136 | Agent loop, acceptance, approval flow, config |
| `tests/security/` | 7 | File path hardening, terminal policy, SSRF protection |
| `tests/tui/` | 5 | PTY entry point tests |
| **Total** | **353** | 65% coverage, 0 ruff warnings |

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch
3. Run `uv run ruff check .` before committing
4. Run `uv run pytest tests/ -q` — all tests must pass
5. Open a pull request

For significant changes, open an issue first to discuss.

---

## Acknowledgments

ATAR is built on the shoulders of giants:

- **[DeepSeek](https://deepseek.com)** — primary AI provider with native tool-calling support
- **[prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)** — the terminal interaction framework
- **[Rich](https://rich.readthedocs.io/)** — beautiful terminal rendering
- **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** — design and interaction reference
- **[Nous Research](https://nousresearch.com)** — pushing the boundaries of open-source AI agents

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

<p align="center">
  <em>Built with clarity. Named for tranquility.</em>
</p>
