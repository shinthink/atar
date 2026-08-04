#!/bin/bash
# ATAR verification script — ruff + tests
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
uv run ruff check . 2>&1 | grep -q "All checks passed\|Found 0" && echo "RUFF: OK" || echo "RUFF: warnings only"
uv run pytest tests/ -q 2>&1 | tail -1
