# Hermes Core Reference Snapshot

```yaml
retrieved_at_utc: "2026-08-02T11:00:00Z"
hermes_version: "0.19.1"
hermes_commit: "85e0073"
source_files_reviewed:
  - "hermes_cli/commands.py" (SlashCommandCompleter, PromptSession)
  - "hermes_cli/cli.py"
  - "agent/runtime.py" (agent loop)
  - "agent/turn_loop.py"
  - "tools/runtime.py"
notes: |
  Hermes uses Rich + prompt_toolkit for its classic REPL.
  No PromptSession found in Hermes sources — uses custom input handling
  with Rich Console.input() and its own SlashCommandCompleter.
  SlashCommandCompleter extends prompt_toolkit Completer.
  Agent loop: prompt assembly → model call → tool execution → result storage → continue.
  Currently ATAR v0.1.0 at commit 931935b.
```
