# ADR-001: Monorepo Structure for ATAR Terminal v1.0

## Status
Accepted

## Context
ATAR Terminal v1.0 requires approximately 25 packages spanning core domains, AI providers, tools, plugins, skills, and tests. The blueprint (Section 5) defines an explicit monorepo directory tree. We must decide the workspace structure and tooling before any package is implemented.

## Decision
Use a single Python monorepo managed by **uv workspaces** with the directory layout defined in `ATAR_TERMINAL_SUPERIORITY_BLUEPRINT.md` Section 5.

- Root `pyproject.toml` defines workspace members under `apps/`, `packages/`, and `providers/`.
- Each package has its own `src/<package>/` layout with an `__init__.py`.
- `tests/` lives at the root for integration and end-to-end tests; unit tests may live within packages.
- `uv lock` manages the single lockfile.
- CI runs across all workspace members.

## Consequences
- Single version, single lockfile — avoids dependency drift between packages.
- All packages share the same Python version (3.12+).
- Adding a new package requires only creating the directory and listing it in the workspace.
- The directory tree matches the blueprint exactly, making it auditable.

## Alternatives Considered
1. **Separate repositories per package** — rejected because versioning dozens of tightly-coupled packages independently creates coordination overhead and makes cross-package refactoring difficult.
2. **Single flat package** — rejected because the blueprint requires clean boundaries between core, providers, tools, and TUI.
3. **Poetry workspaces** — rejected in favor of uv for speed, simplicity, and Python 3.12 focus.

## References
- `ATAR_TERMINAL_SUPERIORITY_BLUEPRINT.md` Section 5
- https://docs.astral.sh/uv/concepts/workspaces/
