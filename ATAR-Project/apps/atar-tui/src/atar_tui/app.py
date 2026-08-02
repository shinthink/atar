"""ATAR TUI — 23 screens. Per blueprint Section 51."""

from __future__ import annotations

import os
import subprocess
import sys

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Static

# ── Functional Screens (7) ──

class ChatScreen(Screen):
    BINDINGS = [("escape", "app.focus_input", "Focus")]

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
            provider = AnthropicProvider(
                base_url="https://api.deepseek.com/anthropic",
                model="deepseek-v4-pro",
            )
            agent = Agent(provider=provider)
            buf: list[str] = []

            async def on_delta(text: str) -> None:
                buf.append(text)

            await agent.run(text, StreamCallbacks(on_delta=on_delta))
            out.write("[dim]" + "".join(buf) + "[/]")
        else:
            out.write("[dim]Set DEEPSEEK_API_KEY for AI.[/]")


class PlanScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(id="plan-input", placeholder="Goal to plan for...")
            yield RichLog(id="plan-output")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        goal = event.value.strip()
        if not goal:
            return
        event.input.value = ""
        out = self.query_one("#plan-output", RichLog)
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        if key:
            from atar_core.agent import Agent
            from atar_core.planning import PlanningEngine
            from atar_provider_anthropic.client import AnthropicProvider
            provider = AnthropicProvider(
                base_url="https://api.deepseek.com/anthropic",
                model="deepseek-v4-pro",
            )
            engine = PlanningEngine(Agent(provider=provider))
            plan = await engine.plan(goal)
            out.write(f"\n[bold]{plan.title or goal}[/]")
            for task in plan.tasks:
                icon = "🔴" if str(task.risk) == "HIGH" else "🟢"
                out.write(f"  {icon} {task.title}")
        else:
            out.write("[dim]Set DEEPSEEK_API_KEY.[/]")


class TasksScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📝 Tasks", classes="t")
            yield Static("Task board: delegated tasks and status")
            yield RichLog(id="task-log")
        yield Footer()


class FilesScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📁 Files", classes="t")
            yield RichLog(id="files-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#files-log", RichLog)
        for f in sorted(os.listdir("."))[:20]:
            log.write(f"  {f}")


class TerminalScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💻 Terminal", classes="t")
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
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            if result.stdout:
                out.write(result.stdout)
            if result.stderr:
                out.write(f"[red]{result.stderr}[/]")
        except Exception as exc:
            out.write(f"[red]{exc}[/]")


class SessionsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💾 Sessions", classes="t")
            yield RichLog(id="session-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#session-log", RichLog)
        from atar_core.session import SessionManager
        for s in SessionManager().list()[:10]:
            log.write(f"  {s.session_id} — {s.title} ({len(s.messages)} msgs)")


class MemoryScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🧠 Memory", classes="t")
            yield RichLog(id="memory-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#memory-log", RichLog)
        from atar_core.memory import MemoryEngine
        for k, v in MemoryEngine().all().items():
            log.write(f"  {k}: {v}")


# ── Informational Screens (16) ──

COSMIKE_BANNER = """\
:::. :::::::::::::::.    :::::::..
  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;
 ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['
c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c
 888   888, 88,   888   888,888b \"88bo,
 YMM   \"\"`  MMM   YMM   \"\"` MMMM   \"W\"
  :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::
  ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''
 ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[
c$$$cc$$$c\"$$c.    \"$$ $$\"\"\"\"   $$$ \"Y$c$$     $$
 888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,
 YMM   \"\"`   `'YMUP\"YMM\"\"\"\"YUMMMMMM     YM     MMM"""


class WelcomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(COSMIKE_BANNER, classes="cosmike"),
            Static(""),
            Static("Clarity in Complexity.", classes="t"),
            Static(""),
            Static("Ctrl+K  Command palette"),
            Static("Ctrl+Q  Quit"),
            Static("Sidebar  Navigate screens"),
            Static(""),
            Static("Set DEEPSEEK_API_KEY to enable AI."),
            id="welcome",
        )
        yield Footer()


class SetupScreen(Screen):
    def compose(self) -> ComposeResult:
        ds = "✅ Set" if os.environ.get("DEEPSEEK_API_KEY") else "❌ Not set"
        an = "✅ Set" if os.environ.get("ANTHROPIC_API_KEY") else "❌ Not set"
        yield Header()
        yield Vertical(
            Static("⚙️ Setup", classes="t"),
            Static(f"DEEPSEEK_API_KEY: {ds}"),
            Static(f"ANTHROPIC_API_KEY: {an}"),
            Static(f"ATAR_HOME: {os.environ.get('ATAR_HOME', os.path.expanduser('~/.atar'))}"),
        )
        yield Footer()


class ProviderScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("🔌 Provider", classes="t"),
            Static("Active: DeepSeek (Anthropic format)"),
            Static("Model: deepseek-v4-pro"),
            Static("Endpoint: api.deepseek.com/anthropic"),
        )
        yield Footer()


class AgentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("🤖 Agents", classes="t"),
            Static("Subagents: delegate tasks with isolated context."),
            Static("Board: queued / running / done."),
        )
        yield Footer()


class SearchScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🔍 Search", classes="t")
            yield Input(id="search-input", placeholder="Search sessions...")
            yield RichLog(id="search-results")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        event.input.value = ""
        out = self.query_one("#search-results", RichLog)
        from atar_core.memory import SessionSearch
        from atar_core.session import SessionManager
        for sess, snippets in SessionSearch(SessionManager()).search(query):
            out.write(f"\n📁 {sess.title}")
            for s in snippets:
                out.write(f"  {s}")


class DiffScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("📊 Diff", classes="t"),
            Static("Run: atar code 'diff' to see changes."),
        )
        yield Footer()


class ProcessScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("⚡ Processes", classes="t"),
            Static("Active subprocesses and background tasks."),
        )
        yield Footer()


class BrowserScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("🌐 Browser", classes="t"),
            Static("Use web_fetch tool or atar code with URLs."),
        )
        yield Footer()


class SkillsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🎯 Skills", classes="t")
            yield RichLog(id="skills-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#skills-log", RichLog)
        from atar_core.skills import SkillRegistry, SkillStatus
        for s in SkillRegistry().list_all():
            icon = "🟢" if s.status == SkillStatus.ACTIVE else "⚪"
            log.write(f"  {icon} {s.name} [{s.status.value}]")


class PluginsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("🔌 Plugins", classes="t"),
            Static("Hook manager: ordered, timeout, failure isolation."),
        )
        yield Footer()


class CheckpointsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("💾 Checkpoints", classes="t")
            yield RichLog(id="checkpoint-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#checkpoint-log", RichLog)
        from atar_core.checkpoint import Checkpoint
        for c in Checkpoint().list():
            log.write(f"  {c['id']} — {c['original']}")


class ApprovalsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("✅ Approvals", classes="t"),
            Static("Destructive tools require approved=True context."),
        )
        yield Footer()


class UsageScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("📈 Usage", classes="t"),
            Static("Token usage tracked per session. Check .atar/audit.log"),
        )
        yield Footer()


class AuditScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("📋 Audit", classes="t"),
            Static("All tool executions logged with correlation IDs."),
        )
        yield Footer()


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("⚙️ Settings", classes="t"),
            Static("Config: ~/.atar/config.yaml"),
            Static("Data: ~/.atar/"),
            Static("Sessions: .atar/sessions.json + .atar/sessions.db"),
            Static("Memory: .atar/memory.json"),
            Static("Skills: .atar/skills.json"),
        )
        yield Footer()


class DiagnosticsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("🔬 Diagnostics", classes="t"),
            Static(f"Python: {sys.version}"),
            Static(f"CWD: {os.getcwd()}"),
            Static(f"ATAR home: {os.path.expanduser('~/.atar')}"),
        )
        yield Footer()


# ── Screen Registry ──

SCREENS: dict[str, type[Screen]] = {
    "welcome": WelcomeScreen, "setup": SetupScreen, "provider": ProviderScreen,
    "chat": ChatScreen, "plan": PlanScreen, "tasks": TasksScreen,
    "agents": AgentsScreen, "files": FilesScreen, "search": SearchScreen,
    "diff": DiffScreen, "terminal": TerminalScreen, "process": ProcessScreen,
    "browser": BrowserScreen, "memory": MemoryScreen, "skills": SkillsScreen,
    "plugins": PluginsScreen, "sessions": SessionsScreen,
    "checkpoints": CheckpointsScreen, "approvals": ApprovalsScreen,
    "usage": UsageScreen, "audit": AuditScreen,
    "settings": SettingsScreen, "diagnostics": DiagnosticsScreen,
}

SIDEBAR: list[tuple[str, str]] = [
    ("👋 Welcome", "welcome"), ("⚙️ Setup", "setup"), ("🔌 Provider", "provider"),
    ("💬 Chat", "chat"), ("📊 Plan", "plan"), ("📝 Tasks", "tasks"),
    ("🤖 Agents", "agents"), ("📁 Files", "files"), ("🔍 Search", "search"),
    ("📊 Diff", "diff"), ("💻 Terminal", "terminal"), ("⚡ Process", "process"),
    ("🌐 Browser", "browser"), ("🧠 Memory", "memory"), ("🎯 Skills", "skills"),
    ("🔌 Plugins", "plugins"), ("💾 Sessions", "sessions"),
    ("💾 Chkpts", "checkpoints"), ("✅ Approvals", "approvals"),
    ("📈 Usage", "usage"), ("📋 Audit", "audit"),
    ("⚙️ Settings", "settings"), ("🔬 Diag", "diagnostics"),
]


class ATARApp(App):
    TITLE = "ATAR AGENT"
    SUB_TITLE = "Clarity in Complexity -- 23 screens"
    CSS = """
    Screen { align: center middle; }
    .t { text-style: bold; color: $accent; padding: 1 0; }
    .cosmike { color: $accent; text-style: bold; }
    #sidebar { width: 16; border: solid $panel; padding: 1 0; background: $surface-darken-1; }
    #sidebar Button { width: 100%; margin: 0; text-align: left; }
    #sidebar .active { background: $accent-darken-2; }
    #main { width: 1fr; padding: 1; }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+k", "command_palette", "Commands"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                for label, screen_id in SIDEBAR:
                    yield Button(label, id=f"nav-{screen_id}")
            with Vertical(id="main"):
                yield Static("", id="main-content")
        yield Footer()

    def on_mount(self) -> None:
        for screen_id, screen_cls in SCREENS.items():
            self.install_screen(screen_cls(), screen_id)
        self.push_screen("welcome")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("nav-"):
            screen_id = bid[4:]
            if screen_id in SCREENS:
                self.switch_screen(screen_id)


def main() -> None:
    ATARApp().run()


if __name__ == "__main__":
    main()
