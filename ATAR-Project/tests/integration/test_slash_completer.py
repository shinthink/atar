"""F9: Slash-command autocomplete overlay tests."""

from __future__ import annotations

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document


class TestSlashCommandCompleter:
    """Verify slash-command completion returns all commands and tools."""

    def test_slash_shows_all_commands(self) -> None:
        """Typing '/' returns all registered slash commands."""
        from atar_cli.rich_repl import SlashCommandToolCompleter, cmd_registry
        c = SlashCommandToolCompleter()
        doc = Document("/", 1)
        completions = list(c.get_completions(doc, CompleteEvent(completion_requested=True)))
        names = {comp.text for comp in completions}
        assert "/help" in names
        assert "/model" in names
        assert "/quit" in names
        # Should return all registered commands
        registered = [x for x in cmd_registry.completions()]
        for r in registered:
            assert r in names or f"/{r.lstrip('/')}" in names, f"Missing command: {r}"

    def test_slash_shows_tools(self) -> None:
        """Typing '/' also shows tools from registry."""
        from atar_cli.rich_repl import SlashCommandToolCompleter
        from atar_tools.registry import list_all
        c = SlashCommandToolCompleter()
        doc = Document("/", 1)
        completions = list(c.get_completions(doc, CompleteEvent(completion_requested=True)))
        names = {comp.text for comp in completions}
        for t in list_all():
            assert f"/{t.name}" in names, f"Missing tool: {t.name}"

    def test_partial_narrows_to_matching(self) -> None:
        """Typing '/mo' narrows to /model only."""
        from atar_cli.rich_repl import SlashCommandToolCompleter
        c = SlashCommandToolCompleter()
        doc = Document("/mo", 3)
        completions = list(c.get_completions(doc, CompleteEvent(completion_requested=True)))
        texts = {comp.text for comp in completions}
        assert "/model" in texts
        # memory starts with mo but might be /remember as primary name
        # Should NOT show unrelated commands
        assert "/help" not in texts

    def test_non_slash_returns_nothing(self) -> None:
        """Typing 'hello' returns no completions."""
        from atar_cli.rich_repl import SlashCommandToolCompleter
        c = SlashCommandToolCompleter()
        doc = Document("hello", 5)
        completions = list(c.get_completions(doc, CompleteEvent(completion_requested=True)))
        assert len(completions) == 0

    def test_spaced_command_returns_nothing(self) -> None:
        """Typing '/model deepseek' returns no completions (arg mode)."""
        from atar_cli.rich_repl import SlashCommandToolCompleter
        c = SlashCommandToolCompleter()
        doc = Document("/model deepseek", 15)
        completions = list(c.get_completions(doc, CompleteEvent(completion_requested=True)))
        assert len(completions) == 0
