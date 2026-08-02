"""ATAR TUI — 23 screens. Per blueprint Section 51."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time

from atar_core.config_reader import get_api_key, save_api_key
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key as events_Key  # noqa: N811
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Static, TextArea

# ── Functional Screens (7) ──

class ApprovalModal(ModalScreen[bool]):
    """Modal: approve or reject a tool execution."""
    tool_name: str = ""
    tool_args: str = ""
    risk: str = "MEDIUM"
    reason: str = ""

    def compose(self) -> ComposeResult:
        yield Static("⚠ Approve Tool Execution?", classes="t")
        yield Static(f"Tool: [bold]{self.tool_name}[/]")
        yield Static(f"Args: [dim]{self.tool_args[:120]}[/]")
        yield Static(f"Risk: [{self._risk_color()}]{self.risk}[/]")
        if self.reason:
            yield Static(f"Reason: {self.reason}")
        yield Static("")
        with Horizontal():
            yield Button("Approve (A)", variant="primary", id="approve-yes")
            yield Button("Reject (R)", variant="error", id="approve-no")
            yield Button("Cancel", id="approve-cancel")

    def _risk_color(self) -> str:
        return {"HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}.get(self.risk, "dim")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve-yes":
            self.dismiss(True)
        elif event.button.id == "approve-no":
            self.dismiss(False)
        else:
            self.dismiss(False)

    def on_key(self, event: events_Key) -> None:
        if event.key == "a":
            self.dismiss(True)
        elif event.key == "r" or event.key == "escape":
            self.dismiss(False)


class ChatScreen(Screen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "send", "Send"),
        ("ctrl+p", "app.quick_file", "Quick File"),
        ("ctrl+l", "app.audit", "Audit"),
    ]

    _task: asyncio.Task | None = None
    _running: bool = False
    _tool_cards: list[dict] = []
    _total_tokens: int = 0
    _total_cost: float = 0.0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield RichLog(id="chat-output", highlight=True, markup=True, max_lines=1000)
            with Horizontal(id="chat-input-area"):
                yield TextArea(id="chat-input", text="")
                yield Button("Send", id="chat-send")
        yield Footer()

    def on_mount(self) -> None:
        out = self.query_one("#chat-output", RichLog)
        key = get_api_key()
        status = "[green]✓ online[/]" if key else "[red]✗ no key[/]"
        out.write(f"[bold cyan]ATAR Chat[/] · {status} · tokens: 0 · $0.000")
        out.write("[dim]/help /clear /model /sessions /status · Ctrl+Enter=send · Shift+Enter=newline[/]")

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
        """Send from TextArea (Ctrl+Enter)."""
        ta = self.query_one("#chat-input", TextArea)
        if ta.text.strip():
            asyncio.create_task(self._send())

    async def _send(self) -> None:
        ta = self.query_one("#chat-input", TextArea)
        out = self.query_one("#chat-output", RichLog)
        text = ta.text.strip()
        if not text or self._running:
            return
        ta.text = ""
        self._running = True

        # Slash commands
        if text.startswith("/"):
            await self._handle_command(text, out)
            self._running = False
            self.query_one("#chat-input", TextArea).focus()
            return

        out.write(f"\n[bold #4FC3F7]▸[/] {text}")

        key = get_api_key()
        if not key:
            out.write("[bold red]No API key. Run Setup first.[/]")
            self._running = False
            self.query_one("#chat-input", TextArea).focus()
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
            ts = str(int(time.time() * 1000))
            icons = {"read_file": "📖", "write_file": "✍️", "terminal": "💻", "web_fetch": "🔎"}
            icon = icons.get(name, "🔧")
            card = {"name": name, "icon": icon, "args": str(args)[:80], "state": "running", "id": ts}
            self._tool_cards.append(card)
            out.write(f"\n[bold #7C3AED]{icon} {name}[/] [dim]{card['args']}[/] [yellow](running)[/]")

        async def on_tool_result(name: str, result: str) -> None:
            # Update matching tool card state
            for c in self._tool_cards:
                if c["name"] == name and c["state"] == "running":
                    c["state"] = "completed"
                    break
            preview = result[:200].replace("\n", " ")
            emoji = "✓" if result else "✗"
            out.write(f"\n[bold #4CAF50]  {emoji} {name}[/] [dim]{preview}[/]")

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
        self._total_tokens += len(text) + len("".join(buf))  # rough estimate
        self._running = False
        self.query_one("#chat-input", TextArea).focus()

    async def _handle_command(self, cmd: str, out: RichLog) -> None:
        cmd = cmd.strip()
        if cmd == "/help":
            out.write("[bold]Slash Commands:[/]")
            out.write("  /help     /clear    /model    /sessions")
            out.write("  /code     /quit     /tools    /status")
        elif cmd == "/tools":
            tools = getattr(self, "_tool_cards", [])
            if not tools:
                out.write("[dim]No tools used yet.[/]")
            else:
                out.write(f"[bold]Tool Activity ({len(tools)} calls):[/]")
                for c in tools:
                    state_icon = "✓" if c["state"] == "completed" else "▶"
                    out.write(f"  {state_icon} {c['icon']} {c['name']} [{c['state']}]")
        elif cmd == "/status":
            out.write("[bold]Agent Status:[/]")
            out.write("  Provider: deepseek-chat")
            out.write(f"  Running: {'yes' if self._running else 'idle'}")
            out.write(f"  Tool calls: {len(self._tool_cards)}")
        elif cmd == "/clear":
            out.clear()
            self._tool_cards = []
        elif cmd == "/quit":
            self.app.exit()
        elif cmd == "/model":
            self.app.push_screen(ModelPicker())
        elif cmd == "/sessions":
            self.app.push_screen(SessionSwitcher())
        elif cmd.startswith("/model"):
            out.write("[yellow]Use Setup screen to change provider/model.[/]")
        else:
            out.write(f"[yellow]Unknown: {cmd}[/]")


class ModelPicker(Screen):
    """Modal: select provider + model with keyboard nav."""
    providers = [
        ("DeepSeek", "deepseek", "deepseek-chat"),
        ("DeepSeek V4", "deepseek", "deepseek-v4-pro"),
        ("OpenAI", "openai", "gpt-4o"),
        ("Anthropic", "anthropic", "claude-sonnet-4-20250514"),
        ("OpenRouter", "openrouter", "deepseek/deepseek-chat"),
        ("Z.AI", "zai", "glm-4"),
    ]
    selected: int = 0

    def compose(self) -> ComposeResult:
        yield Static("📡 Select Model", classes="t")
        yield Static("", id="model-list")
        yield Static("↑↓ navigate · Enter select · Esc cancel", classes="dim")
        yield Footer()

    def on_mount(self) -> None:
        self._render()

    def _render(self) -> None:
        lines = []
        for i, (name, prov, model) in enumerate(self.providers):
            m = "▸" if i == self.selected else " "
            lines.append(f" {m} {name} — [dim]{model}[/] ({prov})")
        self.query_one("#model-list", Static).update("\n".join(lines))

    def on_key(self, event: events_Key) -> None:
        if event.key == "up" and self.selected > 0:
            self.selected -= 1
            self._render()
        elif event.key == "down" and self.selected < len(self.providers) - 1:
            self.selected += 1
            self._render()
        elif event.key == "enter":
            name, prov, model = self.providers[self.selected]
            import json
            import os
            cfg_path = os.path.expanduser("~/.atar/config.json")
            cfg = {}
            try:
                with open(cfg_path) as f:
                    cfg = json.load(f)
            except Exception:
                pass
            cfg["provider"] = prov
            cfg["model"] = model
            os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
            with open(cfg_path, "w") as f:
                json.dump(cfg, f)
            self.app.pop_screen()
            out = self.app.query(".chat-screen RichLog", RichLog) if self.app.query(".chat-screen RichLog") else None
            if out:
                out.first().write(f"[green]✓ Switched to {name} — {model}[/]")
        elif event.key == "escape":
            self.app.pop_screen()


class SessionSwitcher(Screen):
    """Modal: list, switch, resume sessions."""
    selected: int = 0

    def compose(self) -> ComposeResult:
        yield Static("📂 Sessions", classes="t")
        yield Static("", id="session-list")
        yield Static("↑↓ navigate · Enter switch · N new · Esc cancel", classes="dim")
        yield Footer()

    def on_mount(self) -> None:
        from atar_core.session import SessionManager
        self._mgr = SessionManager()
        self._render()

    def _render(self) -> None:
        sessions = self._mgr.list()
        lines = []
        for i, s in enumerate(sessions):
            m = "▸" if i == self.selected else " "
            lines.append(f" {m} {s.title or s.session_id[:12]} — {s.meta.get('messages', 0)} msgs")
        if not lines:
            lines.append("[dim]No saved sessions.[/]")
            lines.append("Press N to create new session.")
        self.query_one("#session-list", Static).update("\n".join(lines))

    def on_key(self, event: events_Key) -> None:
        sessions = self._mgr.list()
        if event.key == "up" and self.selected > 0:
            self.selected -= 1
            self._render()
        elif event.key == "down" and self.selected < len(sessions) - 1:
            self.selected += 1
            self._render()
        elif event.key == "n":
            self._mgr.new()
            self._render()
        elif event.key == "enter" and sessions:
            sess = sessions[self.selected]
            self._mgr._active = sess.session_id
            self.app.pop_screen()
            out = self.app.query(".chat-screen RichLog", RichLog) if self.app.query(".chat-screen RichLog") else None
            if out:
                out.first().write(f"[green]✓ Switched to session: {sess.title or sess.session_id[:12]}[/]")
                for m in getattr(sess, "messages", [])[-10:]:
                    out.first().write(f"[dim]{m.role}: {m.content[:80]}[/]")
        elif event.key == "escape":
            self.app.pop_screen()


class PlanScreen(Screen):
    BINDINGS = [
        ("a", "approve", "Approve"),
        ("r", "reject", "Reject"),
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(id="plan-input", placeholder="Goal to plan — e.g., 'build REST API for blog'")
            yield Static("", id="plan-status")
            yield RichLog(id="plan-output")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        goal = event.value.strip()
        if not goal:
            return
        event.input.value = ""
        out = self.query_one("#plan-output", RichLog)
        status = self.query_one("#plan-status", Static)
        status.update("[yellow]Planning...[/]")

        key = get_api_key()
        if not key:
            out.write("[red]No API key. Run Setup.[/]")
            return

        from atar_core.agent import Agent
        from atar_core.planning import PlanningEngine
        from atar_provider_deepseek.client import DeepSeekProvider
        provider = DeepSeekProvider(api_key=key, model="deepseek-chat")
        engine = PlanningEngine(Agent(provider=provider))

        try:
            plan = await engine.plan(goal)
            out.write(f"\n[bold cyan]Plan: {plan.title or goal}[/]")
            out.write("─" * 40)
            for i, task in enumerate(plan.tasks):
                icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢", "INFO": "🔵"}.get(str(task.risk), "⚪")
                deps = f" ← {task.depends_on}" if hasattr(task, 'depends_on') and task.depends_on else ""
                out.write(f"  {i+1}. {icon} [{task.risk}] {task.title}{deps}")
                if task.description:
                    out.write(f"       [dim]{task.description[:100]}[/]")
            out.write("─" * 40)
            out.write("[dim]A=Approve  R=Reject  Esc=Cancel[/]")
            self._plan = plan
            status.update("[green]✓ Plan generated. Review and approve (A) or reject (R).[/]")
        except Exception as e:
            status.update(f"[red]Error: {e}[/]")

    def action_approve(self) -> None:
        if not hasattr(self, "_plan"):
            return
        out = self.query_one("#plan-output", RichLog)
        out.write("[bold green]✓ Plan approved. Executing...[/]")
        asyncio.create_task(self._execute_plan())

    def action_reject(self) -> None:
        out = self.query_one("#plan-output", RichLog)
        out.write("[yellow]✗ Plan rejected. Revise and try again.[/]")

    async def _execute_plan(self) -> None:
        out = self.query_one("#plan-output", RichLog)
        key = get_api_key()
        if not key:
            return
        from atar_core.agent import Agent, StreamCallbacks
        from atar_provider_deepseek.client import DeepSeekProvider
        provider = DeepSeekProvider(api_key=key, model="deepseek-chat")
        for i, task in enumerate(self._plan.tasks):
            out.write(f"\n[bold]▶ Task {i+1}/{len(self._plan.tasks)}: {task.title}[/]")
            agent = Agent(provider=provider, max_turns=3, tools=[1])
            agent.system_prompt = f"Execute this task: {task.title}. {task.description or ''}"
            # Re-use session messages for continuity
            try:
                _result = await agent.run(
                    f"Execute: {task.title}",
                    StreamCallbacks(on_delta=lambda t: out.write(f"[dim]{t}[/]")),
                )
                out.write("\n[green]  ✓ Done[/]")
            except Exception as e:
                out.write(f"\n[red]  ✗ Failed: {e}[/]")
        out.write("\n[bold green]Plan execution complete.[/]")


class TasksScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📝 Tasks", classes="t")
            yield RichLog(id="task-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#task-log", RichLog)
        try:
            from atar_core.taskboard import TaskBoard
            board = TaskBoard()
            q, r, d = board.status()
            log.write("[bold]Task Board Status[/]")
            log.write(f"  Queued: {q}  Running: {r}  Done: {d}")
            ts = board.list_all()
            if not ts:
                log.write("[dim]  No tasks. Use /delegate in chat.[/]")
            for t in ts:
                icon = {"done": "✓", "running": "▶", "queued": "○"}.get(t.status, "?")
                log.write(f"  {icon} {t.title[:80]}")
        except Exception as e:
            log.write(f"[red]Task board unavailable: {e}[/]")


class FilesScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📁 Files", classes="t")
            yield RichLog(id="files-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#files-log", RichLog)
        import os
        for f in sorted(os.listdir("."))[:30]:
            path = os.path.join(os.getcwd(), f)
            typ = "/" if os.path.isdir(path) else ""
            size = os.path.getsize(path) if os.path.isfile(path) else 0
            log.write(f"  {f}{typ}  [dim]{size}B[/]")


class MemoryScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(id="mem-query", placeholder="Search memory (or press Enter for all)...")
            yield RichLog(id="mem-output")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        out = self.query_one("#mem-output", RichLog)
        from atar_core.memory import MemoryEngine
        mem = MemoryEngine()
        if q:
            for k, v in mem.all().items():
                if q.lower() in k.lower() or q.lower() in str(v).lower():
                    out.write(f"  [bold]{k}[/]: {v}")
        else:
            for k, v in mem.all().items():
                out.write(f"  [bold]{k}[/]: {v}")


class MCPScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🔌 MCP Servers", classes="t")
            yield RichLog(id="mcp-output")
        yield Footer()

    def on_mount(self) -> None:
        out = self.query_one("#mcp-output", RichLog)
        try:
            from atar_core.mcp import MCPManager
            mgr = MCPManager()
            servers = mgr.list()
            if not servers:
                out.write("[dim]No MCP servers configured.[/]")
                out.write("Configure in ~/.atar/mcp.json or use ATAR_MCP env var.")
            for s in servers:
                out.write(f"  {'✓' if s.get('connected') else '✗'} {s.get('name', 'unnamed')}")
        except Exception as e:
            out.write(f"[yellow]MCP: {e}[/]")


class SearchScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Input(id="search-input", placeholder="Search sessions, memory, tools...")
            yield RichLog(id="search-output")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q:
            return
        out = self.query_one("#search-output", RichLog)
        out.clear()
        out.write(f"[bold]Search: {q}[/]")

        # Search sessions
        from atar_core.memory import MemoryEngine, SessionSearch
        from atar_core.session import SessionManager
        sm = SessionManager()
        ss = SessionSearch(sm)
        result_count = 0
        for s, snippets in ss.search(q):
            out.write(f"[bold cyan]Session: {s.title or s.session_id[:12]}[/]")
            for sn in snippets[:3]:
                out.write(f"  [dim]{sn[:100]}[/]")
            result_count += 1

        # Search memory
        mem = MemoryEngine()
        for k, v in mem.all().items():
            if q.lower() in k.lower() or q.lower() in str(v).lower():
                out.write(f"[bold cyan]Memory: {k}[/] = {v}")

        if result_count == 0:
            out.write("[dim]No results. Try different keywords.[/]")


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



class DiffScreen(Screen):
    BINDINGS = [("r", "refresh", "Refresh")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("📊 Git Diff", classes="t")
            yield Static("", id="diff-status")
            yield RichLog(id="diff-log")
        yield Footer()

    def on_mount(self) -> None:
        self._show_diff()

    def action_refresh(self) -> None:
        log = self.query_one("#diff-log", RichLog)
        log.clear()
        self._show_diff()

    def _show_diff(self) -> None:
        log = self.query_one("#diff-log", RichLog)
        status = self.query_one("#diff-status", Static)
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"], capture_output=True, text=True, timeout=5
            )
            if result.stdout:
                status.update("[green]Git diff available[/]")
                log.write(result.stdout)
                log.write("[dim]── Full diff ──[/]")
                r2 = subprocess.run(
                    ["git", "diff"], capture_output=True, text=True, timeout=5
                )
                log.write(r2.stdout[:2000] if r2.stdout else "[dim]Clean working tree.[/]")
            else:
                status.update("[dim]Clean working tree.[/]")
                log.write("No changes to display.")
        except Exception as e:
            status.update(f"[red]Error: {e}[/]")


class ProcessScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("⚡ Processes", classes="t")
            yield RichLog(id="proc-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#proc-log", RichLog)
        try:
            import asyncio
            task = asyncio.current_task()
            if task:
                log.write(f"[bold]Active Task:[/] {task.get_name()}")
            import threading
            for t in threading.enumerate():
                bold = "bold" if t is threading.current_thread() else ""
                end = "/" if t is threading.current_thread() else ""
                log.write(f"  [{bold}]{t.name}[{end}] (daemon={t.daemon})")
        except Exception as e:
            log.write(f"[red]Cannot enumerate threads: {e}[/]")


class BrowserScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🌐 Web Browser", classes="t")
            yield Input(id="browser-url", placeholder="Enter URL to fetch...")
            yield RichLog(id="browser-log")
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "browser-url":
            return
        url = event.value.strip()
        if not url:
            return
        event.input.value = ""
        log = self.query_one("#browser-log", RichLog)
        log.write(f"[bold]Fetching: {url}[/]")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
                resp = await c.get(url, headers={"User-Agent": "ATAR/1.0"})
            log.write(f"[green]HTTP {resp.status_code}[/] {len(resp.text)} bytes")
            log.write(f"[dim]{resp.text[:500]}[/]")
        except Exception as e:
            log.write(f"[red]Error: {e}[/]")


class PluginsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🔌 Plugins", classes="t")
            yield RichLog(id="plugins-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#plugins-log", RichLog)
        try:
            from atar_core.skills import HookManager
            hooks = HookManager()
            registered = hooks.list() if hasattr(hooks, "list") else []
            if registered:
                for r in registered:
                    log.write(f"  • {r}")
            else:
                log.write("[dim]No plugins registered.[/]")
                log.write("Use atar_skills to register plugin hooks.")
        except Exception as e:
            log.write(f"[yellow]Plugin system: {e}[/]")
            log.write("[dim]Create hooks via SkillRegistry.[/]")


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
        with Vertical():
            yield Static("📋 Audit & Replay", classes="t")
            yield RichLog(id="audit-log")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#audit-log", RichLog)
        audit_path = os.path.expanduser("~/.atar/audit.jsonl")
        if os.path.exists(audit_path):
            with open(audit_path) as f:
                lines = f.readlines()[-50:]
            for line in lines:
                try:
                    entry = json.loads(line)
                    log.write(f"[dim]{entry.get('time','')[:19]}[/] {entry.get('action','')} {entry.get('detail','')[:80]}")
                except (json.JSONDecodeError, Exception):
                    log.write(f"[dim]{line[:100]}[/]")
        else:
            log.write("[dim]No audit log yet. Enable auditing in settings.[/]")


class SettingsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("⚙ Settings", classes="t")
            yield Static(f"Python: {sys.version.split()[0]}")
            yield Static(f"Working Dir: {os.getcwd()}")
            yield Static("Config: ~/.atar/config.json")
            yield Static("Sessions: ~/.atar/sessions/")
            yield Static("Audit Log: ~/.atar/audit.jsonl")
            yield Static("Secrets: keyring (primary), env (fallback)")
            yield Static("")
            modes = [
                "safe: ask before destructive operations",
                "normal: auto-approve read-only tools",
                "paranoid: ask for everything",
            ]
            yield Static("[bold]Permission Mode:[/]")
            for m in modes:
                yield Static(f"  {m}")
        yield Footer()


class DiagnosticsScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("🔬 Diagnostics", classes="t")
            yield Static(f"Python: {sys.version}")
            yield Static(f"CWD: {os.getcwd()}")
            yield Static(f"ATAR home: {os.path.expanduser('~/.atar')}")
            yield Static(f"TTY: {sys.stdin.isatty()}")
            yield Static(f"API Key: {'set' if get_api_key() else 'missing'}")
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
        ("ctrl+p", "quick_file", "Quick File"),
        ("ctrl+l", "audit", "Audit"),
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

    def action_quick_file(self) -> None:
        """Jump to Files screen."""
        self.switch_screen("files")

    def action_audit(self) -> None:
        """Jump to Audit screen."""
        self.switch_screen("audit")


def main() -> None:
    ATARApp().run()


if __name__ == "__main__":
    main()
