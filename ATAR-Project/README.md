# ATAR

> **Clarity in Complexity.**

ATAR is a local-first, full-screen terminal AI agent and project operating environment. It converts complex objectives into structured plans, executes approved actions through controlled tools and sandboxes, verifies results using evidence, and retains useful project knowledge without turning memory into noise.

## Philosophy

```text
Clarity before action.
Control before autonomy.
Evidence before conclusion.
Verification before completion.
Memory without noise.
Power without chaos.
```

## Quick Start

```bash
# Install
pip install atar

# Initialize a project
atar init

# Launch the full-screen terminal interface
atar
```

## Architecture

ATAR follows clean architecture principles:

```
interfaces (TUI/CLI)
    ↓
application services
    ↓
domain/core protocols
    ↓
infrastructure implementations
```

See [docs/architecture/](docs/architecture/) for detailed architecture documentation.

## Development

```bash
# Clone and setup
git clone https://github.com/shinthink/atar
cd atar
uv sync
uv run atar
```

## License

MIT
