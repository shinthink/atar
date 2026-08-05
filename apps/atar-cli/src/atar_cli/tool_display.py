"""Animated tool status display using Rich Live."""

from __future__ import annotations

from rich.console import RenderableType
from rich.live import Live
from rich.text import Text


class ToolDisplay:
    """Manages animated tool cards via Rich Live — safe between prompts."""

    def __init__(self, console):
        self._console = console
        self._tools: list[dict] = []
        self._live: Live | None = None

    @property
    def count(self) -> int:
        return len(self._tools)

    def add(self, name: str, detail: str, color: str, icon: str) -> None:
        self._tools.append({"name": name, "detail": detail, "color": color, "icon": icon})

    def remove(self, name: str) -> None:
        self._tools = [t for t in self._tools if t["name"] != name]

    def start(self) -> None:
        if self._live is not None:
            return
        self._live = Live(self._render(), console=self._console, refresh_per_second=8, transient=True)
        self._live.start()

    def stop(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def update(self) -> None:
        if self._live is not None:
            self._live.update(self._render())

    def _render_one(self, tool: dict) -> str:
        c = tool["color"]
        return f"  [{c}]{tool['icon']} {tool['name']}[/] [dim]{tool['detail']}[/] [bold {c}]●[/]"

    def _render(self) -> RenderableType:
        if not self._tools:
            return Text("")
        lines = [self._render_one(t) for t in self._tools]
        return Text("\n".join(lines))
