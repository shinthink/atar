# Contributing to ATAR

Thanks for your interest in contributing! ATAR is an autonomous terminal AI agent — built with clarity, named for tranquility.

## Getting Started

```bash
git clone https://github.com/shinthink/atar
cd ATAR-Project
uv sync
uv run pytest tests/ -q
```

## Development Workflow

1. **Fork** the repository
2. **Create a branch**: `feature/your-feature` or `fix/your-fix`
3. **Write code + tests**: aim for 65%+ coverage on new code
4. **Run checks before committing**:
   ```bash
   uv run ruff check .          # 0 errors required
   uv run pytest tests/ -q      # all tests must pass
   uv run pytest --cov=packages --cov=apps  # check coverage
   ```
5. **Commit** with clear messages following [Conventional Commits](https://www.conventionalcommits.org/)
6. **Open a Pull Request**

## Code Style

- Python 3.12+ with type annotations
- Ruff formatted (line length 200)
- Async-native (`asyncio` + `httpx`)
- Follow existing patterns in `packages/atar-core/` and `packages/atar-tools/`

## Adding a New Tool

1. Create a Python file in `packages/atar-tools/src/atar_tools/tools/`
2. Define an async handler: `async def _my_tool(name, args, ctx) -> ToolResult`
3. Register with `register("tool_name", "description", handler, ...)`
4. Add tests in `tests/contract/`
5. Add to `_TOOL_TOOLSETS` in `packages/atar-tools/src/atar_tools/toolsets.py`

## Adding a New Provider

1. Create directory under `providers/atar-provider-<name>/`
2. Implement `ModelProvider` protocol: `stream()`, `complete()`, `capabilities()`, `health_check()`
3. Register in `packages/atar-core/src/atar_core/provider_registry.py`
4. Add test in `tests/contract/test_providers.py`

## Architecture

```
atar (entry point)
  └── rich_repl.py              prompt_toolkit + Rich REPL
        └── Agent                 multi-turn tool-calling loop
              ├── ProviderRouter   fallback across 6 providers
              ├── Tool Registry    14 tools with auto-discovery
              ├── Memory System    SQLite, secret-filtered, auto-extraction
              ├── Session Manager  SQLite + FTS5 search
              └── Skills/Scheduler/Checkpoints
```

## Project Structure

```
apps/           CLI + TUI applications
packages/       Core libraries (models, protocols, tools, storage, security)
providers/      AI provider clients (DeepSeek, OpenAI, Anthropic, etc.)
plugins/        Auto-discoverable plugin categories
tests/          Contract + integration + security tests
docs/           ADRs, audit reports, research
```

## Questions?

Open an issue or discussion on GitHub.
