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
  <a href="../../actions"><img src="https://img.shields.io/badge/tests-49%2F49-brightgreen?style=for-the-badge" alt="49/49 Tests"></a>
  <a href="../../actions"><img src="https://img.shields.io/badge/RUFF-clean-000000?style=for-the-badge&logo=ruff&logoColor=white" alt="RUFF"></a>
</p>

---

**An autonomous terminal AI agent.** Named after *Ataraxia* — the ancient Greek concept of tranquility through clarity — ATAR operates your terminal with calm precision. Built with Python, prompt_toolkit, and Rich. No cloud dependency, no telemetry, runs locally with your API keys.

---

<table>
<tr><td><b>Autonomous agent loop</b></td><td>Multi-turn tool calling with streaming. The model decides what to do — web_search, web_fetch, read/write files, run terminal commands — and ATAR executes, feeds results back, and continues until the task is complete.</td></tr>
<tr><td><b>Real terminal interface</b></td><td>prompt_toolkit REPL with slash-command autocomplete, multiline editing, streaming Markdown responses, live tool progress cards, interrupt handling, and a persistent status bar showing model, tokens, context usage, and session time.</td></tr>
<tr><td><b>Six AI providers</b></td><td>DeepSeek (native tool calling), OpenAI, Anthropic, OpenRouter, Z.AI, and Custom endpoints. Switch with <code>/model</code> — no code changes. Provider fallback on failure.</td></tr>
<tr><td><b>Live coding tools</b></td><td>Write files, read files, run terminal commands, git operations, run tests — all from the REPL with approval gates and live output streaming.</td></tr>
<tr><td><b>Research capabilities</b></td><td>web_search (DuckDuckGo) and web_fetch for real-time information retrieval. The agent searches, extracts sources, and synthesizes answers with citations.</td></tr>
<tr><td><b>Session persistence</b></td><td>Save and resume conversations with structured tool-call history. Search past sessions. Branch and fork conversations.</td></tr>
<tr><td><b>Theme engine</b></td><td>Built-in atar, monochrome, and high-contrast skins. NO_COLOR support for terminal accessibility. User-configurable themes.</td></tr>
</table>

---

## Quick Install

### Linux

```bash
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync
export DEEPSEEK_API_KEY="your-deepseek-key"
uv run atar
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

---

## Usage

```bash
atar              # Classic REPL (default)
atar --cli         # Force REPL mode
atar --tui         # Full-screen Textual TUI
atar --run "..."   # Single query (non-interactive)
atar --help        # Show all commands
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/model` | Switch AI model provider |
| `/sessions` | Browse and resume saved sessions |
| `/code` | Enter coding mode with file tools |
| `/chat` | Return to chat mode |
| `/help` | Show all available commands |
| `/clear` | Reset conversation |
| `/quit` / `/exit` / `/q` | Exit ATAR |

### Keybindings

| Binding | Action |
|---------|--------|
| `Enter` | Send message |
| `Alt+Enter` | Insert newline |
| `Tab` | Show slash-command completions |
| `Ctrl+C` | Interrupt current agent run |
| `Ctrl+C` twice | Force exit |
| `Ctrl+D` | Exit (with confirmation) |
| `Ctrl+V` | Paste with preview for large content |

---

## Architecture

```
atar (entry point)
  └── rich_repl.py          prompt_toolkit + Rich REPL
        └── Agent             multi-turn tool-calling loop
              ├── ProviderRouter   fallback chain across providers
              ├── Tool Registry    web_search, web_fetch, read_file, write_file, terminal
              ├── Session Manager  JSON persistence + FTS search
              └── Theme Engine     atar / monochrome / high-contrast
```

---

## Development

```bash
# Setup
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync

# Run tests
uv run ruff check .        # Lint
uv run pytest tests/ -q    # 49 tests

# Run ATAR
export DEEPSEEK_API_KEY="your-key"
uv run atar
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Built with clarity. Named for tranquility.
