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
<p align="center"><strong><em>Clarity in Complexity.</em></strong></p>

<p align="center">
  <a href="https://github.com/shinthink/atar/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+"></a>
  <a href="../../actions"><img src="https://img.shields.io/badge/tests-49%2F49-brightgreen?style=for-the-badge" alt="Tests"></a>
</p>

---

**An autonomous terminal AI agent.** Named after *Ataraxia* — the Greek concept of tranquility through clarity. ATAR runs locally with your API keys, your files, and your approval.

---

## Features

- **Autonomous agent loop** — multi-turn tool calling (web_search, web_fetch, read/write files, terminal)
- **Hermes-style REPL** — streaming Markdown, tool progress cards, slash autocomplete, live status bar
- **6 providers** — DeepSeek, OpenAI, Anthropic, OpenRouter, Z.AI, Custom
- **Session persistence** — save/resume conversations with structured history
- **Theme engine** — atar, monochrome, high-contrast skins, NO_COLOR support

## Quick Start

```bash
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync
export DEEPSEEK_API_KEY="your-key"
uv run atar
```

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
