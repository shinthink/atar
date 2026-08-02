"""ATAR TUI — 7-screen terminal application.

Chat, Plan, Tasks, Files, Terminal, Sessions, Memory.
Screen switching via sidebar + Ctrl+K command palette.
"""

from __future__ import annotations

import os

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Static

# ── Screens ──

class ChatScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield RichLog(id="chat-output", highlight=True, markup=True)
            with Horizontal(id="chat-input-area"):
                yield Input(id="chat-input", placeholder="Ask ATAR...")
                yield Button("Send", id="chat-send")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-send":
            await self._send()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            await self._send()

    async def _send(self) -> None:
        inp = self.query_one("#chat-input", Input)
        out = self.query_one("#chat-output", RichLog)
        text = inp.value.strip()
        if not text:
            return
        inp.value = ""
        out.write(f"[bold gold3]▸[/] {text}")
        key = os.environ.get("DEEPSEEK_API_KEY") or ""
        if key:
            from atar_core.agent import Agent, StreamCallbacks
            from atar_provider_anthropic.client import AnthropicProvider
            p = AnthropicProvider(base_url="https://api.deepseek.com/anthropic", model="deepseek-v4-pro")
            agent = Agent(provider=p)
            buf: list[str] = []

            async def d(t: str) -> None:
                buf.append(t)

            await agent.run(text, StreamCallbacks(on_delta=d))
            out.write("[dim]" + "".join(buf) + "[/]")
        else:
            out.write("[dim]Set DEEPSEEK_API_KEY for AI.[/]")


class PlanScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📊 Planning", classes="screen-title")
            yield Input(id="plan-input", placeholder="Goal to plan for...")
            yield RichLog(id="plan-output")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        goal = event.value.strip()
        if not goal:
            return
        event.input.value = ""
        out = self.query_one("#plan-output", RichLog)
        key = os.environ.get("DEEPSEEK_API_KEY") or ""
        if key:
            from atar_core.agent import Agent
            from atar_core.planning import PlanningEngine
            from atar_provider_anthropic.client import AnthropicProvider
            p = AnthropicProvider(base_url="https://api.deepseek.com/anthropic", model="deepseek-v4-pro")
            engine = PlanningEngine(Agent(provider=p))
            plan = await engine.plan(goal)
            out.write(f"\n[bold]{plan.title or goal}[/]")
            for t in plan.tasks:
                icon = "🔴" if str(t.risk) == "HIGH" else "🟢"
                out.write(f"  {icon} {t.title}")
        else:
            out.write("[dim]Set DEEPSEEK_API_KEY.[/]")


class TasksScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📝 Tasks", classes="screen-title")
            yield Static("Task board: delegated tasks and status")
            yield RichLog(id="task-log")
        yield Footer()


class FilesScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📁 Files", classes="screen-title")
            yield Static("File browser — current directory")
            yield RichLog(id="files-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#files-log", RichLog)
        import os as _os
        for f in sorted(_os.listdir("."))[:20]:
            log.write(f"  {f}")


class TerminalScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💻 Terminal", classes="screen-title")
            yield Input(id="term-input", placeholder="$ command...")
            yield RichLog(id="term-output")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        if not cmd:
            return
        event.input.value = ""
        out = self.query_one("#term-output", RichLog)
        out.write(f"\n$ {cmd}")
        import subprocess
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if r.stdout:
                out.write(r.stdout)
            if r.stderr:
                out.write(f"[red]{r.stderr}[/]")
        except Exception as e:
            out.write(f"[red]{e}[/]")


class SessionsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💾 Sessions", classes="screen-title")
            yield RichLog(id="session-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#session-log", RichLog)
        from atar_core.session import SessionManager
        sm = SessionManager()
        for s in sm.list()[:10]:
            log.write(f"  {s.session_id} — {s.title} ({len(s.messages)} msgs)")


class MemoryScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🧠 Memory", classes="screen-title")
            yield RichLog(id="memory-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#memory-log", RichLog)
        from atar_core.memory import MemoryEngine
        m = MemoryEngine()
        for k, v in m.all().items():
            log.write(f"  {k}: {v}")


# ── App ──

class ATARApp(App):
    TITLE = "ATAR Terminal"
    CSS = """
    Screen { align: center middle; }
    .screen-title { text-style: bold; color: $accent; padding: 1 0; }
    #sidebar { width: 18; border: solid $panel; padding: 1 0; }
    #sidebar Button { width: 100%; margin: 0; }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "command_palette", "Commands"),
        ("ctrl+1", "screen_chat", "Chat"),
        ("ctrl+2", "screen_plan", "Plan"),
        ("ctrl+3", "screen_tasks", "Tasks"),
        ("ctrl+4", "screen_files", "Files"),
        ("ctrl+5", "screen_terminal", "Terminal"),
        ("ctrl+6", "screen_sessions", "Sessions"),
        ("ctrl+7", "screen_memory", "Memory"),
    ]

    SCREENS = {
        "chat": ChatScreen,
        "plan": PlanScreen,
        "tasks": TasksScreen,
        "files": FilesScreen,
        "terminal": TerminalScreen,
        "sessions": SessionsScreen,
        "memory": MemoryScreen,
    }

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Button("💬 Chat", id="btn-chat")
                yield Button("📊 Plan", id="btn-plan")
                yield Button("📝 Tasks", id="btn-tasks")
                yield Button("📁 Files", id="btn-files")
                yield Button("💻 Terminal", id="btn-terminal")
                yield Button("💾 Sessions", id="btn-sessions")
                yield Button("🧠 Memory", id="btn-memory")
            with Vertical(id="main"):
                yield Static("ATAR Terminal — Ctrl+K for commands, click sidebar to navigate", id="placeholder")
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen("chat")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        mapping = {
            "btn-chat": "chat", "btn-plan": "plan", "btn-tasks": "tasks",
            "btn-files": "files", "btn-terminal": "terminal",
            "btn-sessions": "sessions", "btn-memory": "memory",
        }
        screen = mapping.get(event.button.id or "")
        if screen:
            self.switch_screen(screen)

    def action_screen_chat(self) -> None: self.switch_screen("chat")
    def action_screen_plan(self) -> None: self.switch_screen("plan")
    def action_screen_tasks(self) -> None: self.switch_screen("tasks")
    def action_screen_files(self) -> None: self.switch_screen("files")
    def action_screen_terminal(self) -> None: self.switch_screen("terminal")
    def action_screen_sessions(self) -> None: self.switch_screen("sessions")
    def action_screen_memory(self) -> None: self.switch_screen("memory")


def main() -> None:
    ATARApp().run()


if __name__ == "__main__":
    main()
