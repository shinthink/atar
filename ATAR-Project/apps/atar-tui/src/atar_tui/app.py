"""ATAR TUI — Textual full-screen terminal application skeleton per Section 7."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static


class ATARApp(App):
    """ATAR full-screen terminal application."""

    TITLE = "ATAR"
    SUB_TITLE = "Clarity in Complexity"
    CSS = """
    #sidebar {
        width: 20;
        border: solid $primary;
    }
    #main {
        width: 1fr;
    }
    #output {
        height: 1fr;
    }
    #input {
        height: 3;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "command_palette", "Commands"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("Overview")
                yield Static("Chat")
                yield Static("Plan")
                yield Static("Tasks")
                yield Static("Files")
            with Vertical(id="main"):
                yield RichLog(id="output", highlight=True, markup=True)
                yield Input(id="input", placeholder="Ask ATAR or press Ctrl+K")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        output = self.query_one("#output", RichLog)
        output.write(f"[bold gold3]▸[/] {event.value}")
        output.write("[dim]◉  Thinking...[/]")
        output.write("●  ATAR v0.1.0 — agent core ready.")
        event.input.clear()

    def action_quit(self) -> None:
        self.exit()


def main() -> None:
    ATARApp().run()


if __name__ == "__main__":
    main()
