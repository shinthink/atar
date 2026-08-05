"""Tool status display — clean single-line cards, no animation."""

from __future__ import annotations


class ToolDisplay:
    """Clean tool cards — one line per tool, no animation conflicts."""

    def __init__(self, console):
        self._console = console
        self._tools: list[dict] = []
        self._shown: set[str] = set()

    @property
    def count(self) -> int:
        return len(self._tools)

    def add(self, name: str, detail: str, color: str, icon: str) -> None:
        # Deduplicate by tool call
        key = f"{name}:{detail}"
        if key in self._shown:
            return
        self._shown.add(key)
        self._tools.append({"name": name, "detail": detail, "color": color, "icon": icon})
        # Print immediately — one line, clean
        c = color
        self._console.print(f"  [{c}]{icon} {name}[/] [dim]{detail}[/]")

    def remove(self, name: str) -> None:
        self._tools = [t for t in self._tools if t["name"] != name]

    def start(self) -> None:
        pass  # No animation — tools print as they appear

    def stop(self) -> None:
        pass

    def update(self) -> None:
        pass
