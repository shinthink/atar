"""ATAR command registry — slash commands, aliases, categories, autocomplete."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

# Handler: async function that takes (args: str) -> None
CommandHandler = Callable[[str], Awaitable[None]]


@dataclass
class SlashCommand:
    """Definition of a slash command."""
    name: str                          # canonical name: "/model"
    aliases: list[str] = field(default_factory=list)  # ["/m"]
    description: str = ""
    category: str = "general"          # session, model, tools, memory, skills, system
    arg_hint: str = ""                 # "[name]" for /model [name]
    handler: CommandHandler | None = None

    @property
    def all_names(self) -> list[str]:
        return [self.name] + self.aliases

    @property
    def display(self) -> str:
        hint = f" {self.arg_hint}" if self.arg_hint else ""
        return f"{self.name}{hint}"


class CommandRegistry:
    """Central registry for all slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}
        self._by_category: dict[str, list[SlashCommand]] = {}

    def register(self, cmd: SlashCommand) -> None:
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd
        self._by_category.setdefault(cmd.category, []).append(cmd)

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    def list_all(self) -> list[SlashCommand]:
        seen = set()
        result = []
        for cmd in self._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(cmd)
        return sorted(result, key=lambda c: c.name)

    def list_by_category(self) -> dict[str, list[SlashCommand]]:
        return dict(self._by_category)

    def names(self) -> list[str]:
        return list(self._commands.keys())

    def completions(self) -> list[str]:
        """Return list of command names for autocomplete."""
        return sorted(set(self._commands.keys()))


# Global instance
registry = CommandRegistry()


def register_command(
    name: str,
    description: str,
    aliases: list[str] | None = None,
    category: str = "general",
    arg_hint: str = "",
    handler: CommandHandler | None = None,
) -> SlashCommand:
    """Register a slash command and return it."""
    cmd = SlashCommand(
        name=name,
        aliases=aliases or [],
        description=description,
        category=category,
        arg_hint=arg_hint,
        handler=handler,
    )
    registry.register(cmd)
    return cmd
