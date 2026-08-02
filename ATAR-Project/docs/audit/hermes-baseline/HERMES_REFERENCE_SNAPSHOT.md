# HERMES REFERENCE SNAPSHOT

```yaml
audited_at_utc: 2026-08-02
stable_release: latest
stable_release_tag: UNKNOWN — release page not accessible
main_commit: UNKNOWN — live inspection blocked
docs_deployment_date: 2026-07
docs_url: https://hermes-agent.nousresearch.com/docs
llms_index: retrieved via browser
llms_toc_hash: 17458 bytes — full index captured
tools_reference_url: /docs/reference/tools-reference/
toolsets_reference_url: /docs/reference/toolsets-reference/
slash_commands_url: /docs/reference/cli-commands/
skills_catalog_url: /docs/reference/skills-catalog/
repository: https://github.com/NousResearch/hermes-agent
auditor: ATAR build agent
```

## Key Hermes Features (from llms.txt index)

### Terminal Interface
- CLI: commands, keybindings, personalities
- TUI: Ink terminal, mouse, themes, sessions
- REPL: classic prompt_toolkit REPL
- Skins/themes: configurable, NO_COLOR support

### Agent Runtime
- Agent loop: tool calling, streaming, multi-turn
- Provider runtime: 20+ providers
- Tool registry: central registry with schemas
- Sessions: persistence, resume, search

### Tools
- File: read, write, search, patch
- Terminal: execute, background, process mgmt
- Web: search, browser, vision
- Memory: persistent, session search
- Delegation: subagents, task board
- Cron: scheduled jobs
- MCP: server integration

### Coding
- Checkpoint/rollback: pre-write snapshots
- Diff viewer, worktrees
- Batch/evaluation

### Security
- Approval system: risk-based, modal
- Credential pools, keyring
- Path protection, symlink detection
