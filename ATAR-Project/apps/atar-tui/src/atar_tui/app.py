"""ATAR TUI — 23 screens. Per blueprint Section 51."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys

from atar_core.config_reader import get_api_key, save_api_key
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key as events_Key  # noqa: N811
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Static

# ── Functional Screens (7) ──

class ChatScreen(Screen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "send", "Send"),
    ]

    _task: asyncio.Task | None = None
    _running: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield RichLog(id="chat-output", highlight=True, markup=True, max_lines=1000)
            with Horizontal(id="chat-input-area"):
                yield Input(id="chat-input", placeholder="Ask ATAR...  /help for commands")
                yield Button("Send", id="chat-send")
        yield Footer()

    def on_mount(self) -> None:
        out = self.query_one("#chat-output", RichLog)
        out.write("[bold cyan]ATAR Chat[/] — streaming conversation with tools")
        out.write("[dim]Type /help for commands, Ctrl+Enter to send[/]")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "chat-send":
            await self._send()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input" and not self._running:
            await self._send()

    def action_cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            self._running = False
            out = self.query_one("#chat-output", RichLog)
            out.write("[bold yellow]⏹ Cancelled[/]")

    def action_send(self) -> None:
        """Send from multiline textarea."""
        inp = self.query_one("#chat-input", Input)
        if inp.value.strip():
            asyncio.create_task(self._send())

    async def _send(self) -> None:
        inp = self.query_one("#chat-input", Input)
        out = self.query_one("#chat-output", RichLog)
        text = inp.value.strip()
        if not text or self._running:
            return
        inp.value = ""
        self._running = True

        # Slash commands
        if text.startswith("/"):
            await self._handle_command(text, out)
            self._running = False
            self.query_one("#chat-input", Input).focus()
            return

        out.write(f"\n[bold #4FC3F7]▸[/] {text}")

        key = get_api_key()
        if not key:
            out.write("[bold red]No API key. Run Setup first.[/]")
            self._running = False
            self.query_one("#chat-input", Input).focus()
            return

        import atar_tools.tools.file  # noqa: F401
        from atar_core.agent import Agent, StreamCallbacks
        from atar_provider_deepseek.client import DeepSeekProvider

        provider = DeepSeekProvider(api_key=key, model="deepseek-chat")
        agent = Agent(provider=provider, max_turns=5, tools=[1])
        agent.system_prompt = (
            "You are ATAR. Use tools: read_file, write_file, terminal, web_fetch. "
            "Be concise. Verify before acting."
        )

        buf: list[str] = []

        async def on_delta(t: str) -> None:
            buf.append(t)
            # Stream partial text to display
            if len(buf) == 1:
                out.write("\n[dim]")
            out.write(t)

        async def on_tool(name: str, args: dict) -> None:
            icons = {"read_file": "📖", "write_file": "✍️", "terminal": "💻", "web_fetch": "🔎"}
            icon = icons.get(name, "🔧")
            out.write(f"\n[bold #7C3AED]{icon} {name}[/] [dim]{str(args)[:100]}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            preview = result[:200].replace("\n", " ")
            out.write(f"\n[bold #4CAF50]  ✓ {name}[/] [dim]{preview}[/]")

        try:
            self._task = asyncio.create_task(
                agent.run(text, StreamCallbacks(
                    on_delta=on_delta,
                    on_tool_call=on_tool,
                    on_tool_result=on_tool_result,
                ))
            )
            await self._task
        except asyncio.CancelledError:
            out.write("[dim][Cancelled][/]")
        except Exception as e:
            out.write(f"\n[red]Error: {e}[/]")

        out.write("\n")
        self._running = False
        self.query_one("#chat-input", Input).focus()

    async def _handle_command(self, cmd: str, out: RichLog) -> None:
        cmd = cmd.strip()
        if cmd == "/help":
            out.write("[bold]Commands:[/]\n  /help /clear /model /code /quit")
        elif cmd == "/clear":
            out.clear()
        elif cmd == "/quit":
            self.app.exit()
        elif cmd.startswith("/model"):
            out.write("[yellow]Use Setup screen to change provider/model.[/]")
        else:
            out.write(f"[yellow]Unknown: {cmd}[/]")


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
        key = get_api_key()
        if key:
            from atar_core.agent import Agent
            from atar_core.planning import PlanningEngine
            from atar_provider_anthropic.client import AnthropicProvider
            provider = AnthropicProvider(
                api_key=key, base_url="https://api.deepseek.com/anthropic",
                model="deepseek-v4-pro",
            )
            engine = PlanningEngine(Agent(provider=provider))
            plan = await engine.plan(goal)
            out.write(f"\n[bold]{plan.title or goal}[/]")
            for task in plan.tasks:
                icon = "🔴" if str(task.risk) == "HIGH" else "🟢"
                out.write(f"  {icon} {task.title}")
        else:
            out.write("[bold red]No API key configured.[/]")


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
    """First-run setup wizard: provider → key → model → test → done."""
    providers = [
        ("DeepSeek", "deepseek", "https://api.deepseek.com/v1", "deepseek-chat"),
        ("OpenAI", "openai", "https://api.openai.com/v1", "gpt-4o"),
        ("Anthropic", "anthropic", "https://api.anthropic.com", "claude-sonnet-4-20250514"),
        ("OpenRouter", "openrouter", "https://openrouter.ai/api/v1", "deepseek/deepseek-chat"),
        ("Z.AI", "zai", "https://api.z.ai", "glm-4"),
        ("Custom", "custom", "", ""),
    ]
    step: int = 1
    selected: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="setup-body"):
            yield Static("⚡ ATAR First-Run Setup", classes="t")
            yield Static("")
            yield Static("Clarity in Complexity — Ataraxia", classes="dim")
            yield Static("")
            yield Static("Select your AI provider:", id="setup-prompt")
            yield Static("", id="provider-list")
            yield Input(id="setup-input", placeholder="Enter API key (sk-...)")
            yield Static("", id="setup-status")
        yield Footer()

    def on_mount(self) -> None:
        self._render_providers()
        self.query_one("#setup-input").display = False

    def _render_providers(self) -> None:
        lines = []
        for i, (name, _key_id, url, model) in enumerate(self.providers):
            marker = "▸" if i == self.selected else " "
            lines.append(f" {marker} {name} — {url}/{model}")
        self.query_one("#provider-list", Static).update("\n".join(lines))

    def on_key(self, event: events_Key) -> None:
        if self.step == 1:
            if event.key == "up" and self.selected > 0:
                self.selected -= 1
                self._render_providers()
            elif event.key == "down" and self.selected < len(self.providers) - 1:
                self.selected += 1
                self._render_providers()
            elif event.key == "enter":
                self.step = 2
                name, self._prov_id, _, _ = self.providers[self.selected]
                self.query_one("#provider-list").display = False
                self.query_one("#setup-prompt", Static).update(f"Enter API key for [bold]{name}[/]:")
                inp = self.query_one("#setup-input")
                inp.display = True
                inp.focus()
        elif self.step == 2 and event.key == "escape":
            self.step = 1
            self.query_one("#setup-input").display = False
            self._render_providers()
            self.query_one("#provider-list").display = True
            self.query_one("#setup-prompt", Static).update("Select your AI provider:")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "setup-input" or self.step != 2:
            return
        key = event.value.strip()
        if not key:
            self.query_one("#setup-status", Static).update("[red]Empty key.[/]")
            return
        event.input.value = ""
        status = self.query_one("#setup-status", Static)

        status.update("[yellow]Testing auth...[/]")
        name, prov_id, base_url, model = self.providers[self.selected]
        save_api_key(prov_id, key)
        status.update("[bold green]✓ Key saved securely.[/]")

        # Test auth
        try:
            ok, msg = await self._test_auth(prov_id, key, base_url, model)
            if ok:
                status.update(f"[bold green]✓ Auth OK — {msg}[/]")
                # Save provider preference
                import json
                import os
                cfg_path = os.path.expanduser("~/.atar/config.json")
                cfg = {}
                try:
                    with open(cfg_path) as f:
                        cfg = json.load(f)
                except Exception:
                    pass
                cfg["provider"] = prov_id
                cfg["model"] = model
                cfg["base_url"] = base_url
                os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
                with open(cfg_path, "w") as f:
                    json.dump(cfg, f)
                self.query_one("#setup-body").query(Input).first().display = False
                self.query_one("#setup-prompt", Static).update("[bold green]Setup complete![/]")
                self.query_one("#setup-status", Static).update("Press [bold]Ctrl+W[/] to go to Welcome screen.")
            else:
                status.update(f"[red]✗ Auth failed: {msg}[/]")
        except Exception as e:
            status.update(f"[red]Error: {e}[/]")

    async def _test_auth(self, provider_id: str, key: str, base_url: str, model: str) -> tuple[bool, str]:
        import httpx
        if provider_id in ("deepseek", "openai", "openrouter", "zai", "custom"):
            url = f"{base_url}/models" if base_url else "https://api.deepseek.com/v1/models"
            headers = {"Authorization": f"Bearer {key}"}
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return True, f"{model}"
                return False, f"HTTP {resp.status_code}"
            except Exception as e:
                return False, str(e)
        elif provider_id == "anthropic":
            url = f"{base_url}/v1/messages" if base_url else "https://api.anthropic.com/v1/messages"
            headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        url,
                        json={"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]},
                        headers=headers,
                    )
                if resp.status_code in (200, 400, 429):
                    return True, f"{model}"
                return False, f"HTTP {resp.status_code}"
            except Exception as e:
                return False, str(e)
        return False, "Unknown provider"


class ProviderScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🔌 Provider", classes="t")
            yield Static("", id="provider-info")
        yield Footer()

    def on_mount(self) -> None:
        info = self.query_one("#provider-info", Static)
        import os

        from atar_core.config_reader import get_api_key
        cfg_path = os.path.expanduser("~/.atar/config.json")
        cfg = {}
        try:
            with open(cfg_path) as f:
                cfg = json.load(f)
        except Exception:
            pass
        lines = [
            f"Provider: {cfg.get('provider', 'deepseek')}",
            f"Model: {cfg.get('model', 'deepseek-chat')}",
            f"Base URL: {cfg.get('base_url', 'https://api.deepseek.com/v1')}",
            f"Key: {'✓ configured' if get_api_key() else '✗ not set'}",
        ]
        info.update("\n".join(lines))


class AgentsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🤖 Agents", classes="t")
            yield Static("Subagents: delegate tasks with isolated context.")
            yield Static("Board: queued / running / done.")
            yield Static("")
            yield Static("Use [bold]atar delegate[/] or [bold]/delegate[/] in chat.")
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
    .t { text-style: bold; color: #4FC3F7; padding: 1 0; }
    .cosmike { color: #29B6F6; text-style: bold; }
    #sidebar { width: 16; border: solid #0288D1; padding: 1 0; background: #0D47A1; }
    #sidebar Button { width: 100%; margin: 0; text-align: left; color: #B3E5FC; }
    #sidebar Button:hover { background: #1565C0; color: #E1F5FE; }
    #sidebar .active { background: #0277BD; }
    #main { width: 1fr; padding: 1; }
    #welcome { color: #E1F5FE; }
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
        from atar_core.config_reader import is_first_run
        start = "setup" if is_first_run() else "welcome"
        self.push_screen(start)

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
