# ATAR v0.1.0 — "Clarity Begins"

First controlled release of ATAR Terminal.

## Capabilities
- **Chat**: Real-time AI conversation via DeepSeek API (Anthropic format)
- **Plan**: Structured task planning with risk classification and approval gates
- **Code**: Codebase analysis with tool suggestions (git, terminal, file, test)
- **Sessions**: Persistent conversations with `--session` resume
- **Tools**: read_file, write_file, terminal, git, test_runner

## Architecture
- Python 3.12+, async-native (httpx + asyncio)
- Clean architecture: models → protocols → core → adapters
- Monorepo: 9 packages, 3 tools
- Provider: Anthropic Messages API adapter (+ DeepSeek compatible)

## Tests
- 33 contract + integration tests
- Ruff lint clean
- Real API integration verified with DeepSeek

## Installation
```bash
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync
export DEEPSEEK_API_KEY="sk-..."
uv run atar chat "hello"
```

## Commands
- `atar chat "prompt"` — Chat with AI
- `atar chat --session <id> "prompt"` — Resume session
- `atar plan "goal"` — Generate structured plan
- `atar plan --yes "goal"` — Auto-approve plan
- `atar code "question"` — Analyze codebase
- `atar init` — Initialize project

## Known Limitations
- Tool execution is descriptive (model describes, user runs)
- DeepSeek Anthropic endpoint has no structured tool calling
- No Textual TUI (CLI only for v0.1)
- Sessions stored as JSON (SQLite coming in v0.2)
- No multi-agent, browser, MCP, voice, skills
