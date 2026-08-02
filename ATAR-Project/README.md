<!-- ATAR CLI banner -->
<pre>
  :::. :::::::::::::::.    :::::::..         :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::
  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;        ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''
 ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['       ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[
c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c        c$$$cc$$$c"$$c.    "$$ $$""""   $$$ "Y$c$$     $$
 888   888, 88,   888   888,888b "88bo,     888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,
 YMM   ""`  MMM   YMM   ""` MMMM   "W"      YMM   ""`   `'YMUP"YMM""""YUMMMMMM     YM     MMM

Clarity in Complexity.
</pre>

# ATAR

> *Clarity in Complexity.*

ATAR is an autonomous terminal AI agent — a classic REPL with real-time tool execution, streaming responses, and persistent sessions. Inspired by the Stoic concept of **Ataraxia** (tranquility of mind), ATAR operates with calm precision.

## Features

- **Autonomous agent loop** — multi-turn tool calling with web_search, web_fetch, read/write files, terminal commands
- **Hermes-style REPL** — streaming Markdown responses, tool progress cards, slash-command autocomplete
- **Live status bar** — model, token usage, context bar, response time, session timer
- **6 providers** — DeepSeek, OpenAI, Anthropic, OpenRouter, Z.AI, Custom
- **Session persistence** — save/resume conversations
- **Theme engine** — atar, monochrome, high-contrast skins

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
| `/model` | Switch AI model |
| `/sessions` | Manage sessions |
| `/code` | Coding mode |
| `/chat` | Chat mode |
| `/help` | Show commands |
| `/clear` | Reset |
| `/quit` | Exit |

## Architecture

```
atar → rich_repl.py → Agent (tool loop) → ProviderRouter → Tools → Session
```

## Development

```bash
uv sync && uv run ruff check . && uv run pytest tests/ -q
```

## License

Apache 2.0
