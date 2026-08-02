"""ATAR TUI — working interactive chat with streaming.

Per blueprint Section 7, Section 51. Full-screen Textual application.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static


class ATARApp(App):
    TITLE = "ATAR Terminal"
    SUB_TITLE = "Clarity in Complexity"

    CSS = """
    #sidebar {
        width: 22;
        border: solid $primary-darken-2;
        background: $surface-darken-1;
        padding: 1;
    }
    #sidebar Static {
        padding: 0 1;
        height: 1;
    }
    #sidebar .active {
        color: $accent;
        text-style: bold;
    }
    #main {
        width: 1fr;
    }
    #output {
        height: 1fr;
        padding: 1;
    }
    #thinking {
        height: 1;
        color: $text-disabled;
        padding: 0 1;
    }
    #input-area {
        height: auto;
        border-top: solid $panel;
        padding: 1;
    }
    #input {
        width: 100%;
    }
    .user-msg {
        color: $accent;
        text-style: bold;
        margin: 1 0 0 0;
    }
    .agent-msg {
        margin: 0 0 1 0;
        color: $text;
    }
    .thinking-msg {
        color: $text-disabled;
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "command_palette", "Commands"),
        ("escape", "focus_input", "Focus input"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("📋 Chat", classes="active")
                yield Static("📊 Plan")
                yield Static("📝 Tasks")
                yield Static("💾 Sessions")
                yield Static("🧠 Memory", classes="")
                yield Static("🔧 Tools")
            with Vertical(id="main"):
                yield VerticalScroll(id="output")
                yield Static("", id="thinking")
                with Horizontal(id="input-area"):
                    yield Input(id="input", placeholder="Ask ATAR... (Ctrl+Q to quit)")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#input", Input).focus()
        self._provider = None
        self._messages: list = []

    def _get_provider(self):
        if self._provider is None:
            import os

            from atar_provider_anthropic.client import AnthropicProvider
            key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
            if key:
                self._provider = AnthropicProvider(
                    base_url="https://api.deepseek.com/anthropic", model="deepseek-v4-pro"
                )
            else:
                from atar_core.fake_provider import FakeModelProvider
                self._provider = FakeModelProvider(responses=["Set DEEPSEEK_API_KEY in env for real AI."])
        return self._provider

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value.strip():
            return

        user_text = event.value.strip()
        event.input.clear()
        output = self.query_one("#output", VerticalScroll)
        thinking = self.query_one("#thinking", Static)
        inp = self.query_one("#input", Input)
        inp.disabled = True

        # Show user message
        output.mount(Static(f"▸ {user_text}", classes="user-msg"))
        thinking.update("◉ Thinking...")

        # Run agent
        from atar_core.agent import Agent, StreamCallbacks
        from atar_models.requests import Message

        provider = self._get_provider()
        agent = Agent(provider=provider, session_id="tui-session")
        for msg in self._messages:
            agent._messages.append(msg)

        buf: list[str] = []

        async def on_delta(text: str) -> None:
            buf.append(text)

        response = await agent.run(user_text, StreamCallbacks(on_delta=on_delta))
        _ = response  # consumed via streaming callbacks
        thinking.update("")

        full_text = "".join(buf)
        if full_text:
            output.mount(Static(full_text, classes="agent-msg"))
            self._messages.append(Message(role="user", content=user_text))
            self._messages.append(Message(role="assistant", content=full_text))

        output.scroll_end(animate=False)
        inp.disabled = False
        inp.focus()

    def action_focus_input(self) -> None:
        self.query_one("#input", Input).focus()

    def action_quit(self) -> None:
        self.exit()


def main() -> None:
    ATARApp().run()


if __name__ == "__main__":
    main()
