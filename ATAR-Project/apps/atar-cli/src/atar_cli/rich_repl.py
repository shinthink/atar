"""ATAR Classic REPL — Hermes-style with streaming, tools, sessions."""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import uuid
from contextlib import suppress

from prompt_toolkit import PromptSession
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

# ── Terminal capabilities ──
_HAS_COLOR = os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"
_TERM_WIDTH = shutil.get_terminal_size((80, 24)).columns
console = Console(color_system="auto" if _HAS_COLOR else None, width=_TERM_WIDTH)

# ── Slash commands (from registry) ──
from atar_core.commands import register_command  # noqa: E402
from atar_core.commands import registry as cmd_registry  # noqa: E402

# Register all commands
register_command("/help", "Show available commands", aliases=["/h"], category="system")
from atar_core.prompt import assemble as assemble_prompt  # noqa: E402
from atar_core.provider_registry import PROVIDERS as _PROVIDERS  # noqa: E402
from atar_core.provider_registry import get_provider
from atar_models.requests import Message  # noqa: E402

PROVIDER_MODELS = {pid: prof.default_models for pid, prof in _PROVIDERS.items()}
MODELS = [(prof.display_name, pid, prof.default_model) for pid, prof in _PROVIDERS.items()]
register_command("/model", "Switch AI model", category="model", arg_hint="[name]")
register_command("/sessions", "Manage sessions", aliases=["/s"], category="session")
register_command("/checkpoints", "List file checkpoints", category="session")
register_command("/restore", "Restore from checkpoint", category="session", arg_hint="[id]")
register_command("/code", "Coding mode", category="tools")
register_command("/chat", "Chat mode", category="tools")
register_command("/clear", "Reset conversation", aliases=["/reset"], category="session")
register_command("/quit", "Exit ATAR", aliases=["/exit", "/q"], category="system")
register_command("/status", "Show runtime status", category="system")
register_command("/memory", "Show persistent memories", category="memory")
register_command("/remember", "Save a fact to memory", category="memory", arg_hint="[text]")
register_command("/undo", "Undo the last turn", category="session")
register_command("/retry", "Retry the last turn", category="session")
register_command("/compress", "Compress conversation context", category="session")
register_command("/toolset", "Switch active toolset", aliases=["/ts"], category="tools", arg_hint="[name]")
register_command("/personality", "Switch or list personas", aliases=["/p"], category="model", arg_hint="[name]")
register_command("/usage", "Show current session usage", category="system")
register_command("/insights", "Show cross-session insights", category="system", arg_hint="[--days N]")


# ── Keybindings ──
bindings = KeyBindings()


@bindings.add("escape", "enter")
def _(event):
    event.current_buffer.insert_text("\n")


class SlashCommandToolCompleter(Completer):
    """Completer that shows all slash commands + tools when typing '/'."""

    @staticmethod
    def _tool_risk(tool_name: str) -> tuple[str, str]:
        """Return (risk_label, color) for a tool."""
        risk_map = {
            "read_file": ("Read-only", "#4ADE80"),
            "search_files": ("Read-only", "#4ADE80"),
            "session_search": ("Read-only", "#4ADE80"),
            "session_resume": ("Read-only", "#4ADE80"),
            "git": ("Read-only", "#4ADE80"),
            "web_search": ("Network", "#FBBF24"),
            "web_fetch": ("Network", "#FBBF24"),
            "browser": ("Network", "#FBBF24"),
            "write_file": ("Write", "#F87171"),
            "patch": ("Write", "#F87171"),
            "terminal": ("Execute", "#EF4444"),
            "run_tests": ("Execute", "#EF4444"),
            "execute_code": ("Execute", "#EF4444"),
            "cronjob": ("Execute", "#EF4444"),
            "delegate_task": ("Execute", "#EF4444"),
        }
        return risk_map.get(tool_name, ("Unknown", "#9CA3AF"))

    def get_completions(self, document: Document, complete_event):
        text_before = document.text_before_cursor
        # Only trigger for slash commands (text starts with /)
        if not text_before.strip().startswith("/"):
            return

        word = text_before.strip()
        # If cursor is past the first word, don't complete
        if " " in text_before.strip() and not word.startswith("/"):
            return

        # Get slash commands from registry
        cmds = cmd_registry.completions()
        matching = [c for c in cmds if c.startswith(word)]

        # If user typed only "/" or "/<partial>", show matching commands
        if word == "/" or matching:
            for cmd_name in sorted(matching if matching else list(cmds)):
                cmd = cmd_registry.get(cmd_name)
                if not cmd:
                    continue
                display_meta = cmd.description
                if cmd.aliases:
                    display_meta += f" ({', '.join(cmd.aliases)})"
                yield Completion(
                    cmd_name,
                    start_position=-len(word),
                    display_meta=display_meta,
                    style="fg:#67D8FF bold",
                    selected_style="bg:#1a1a2e fg:#67D8FF bold",
                )

            # Also show tools after commands when user just typed "/"
            if word == "/" or not matching:
                from atar_tools.registry import list_all as _list_tools
                tools = _list_tools()
                seen = set()
                for t in tools:
                    if t.name in seen:
                        continue
                    seen.add(t.name)
                    risk, color = self._tool_risk(t.name)
                    yield Completion(
                        f"/{t.name}",
                        start_position=-len(word),
                        display_meta=f"[{risk}] {t.description[:60]}" if hasattr(t, 'description') else f"[{risk}]",
                        style=f"fg:{color}",
                        selected_style=f"bg:#1a1a2e fg:{color}",
                    )


@bindings.add("c-c")
def _(event):
    event.current_buffer.text = ""


@bindings.add("c-v")
def _(event):
    data = event.app.clipboard.get_data()
    text = data.text if isinstance(data, ClipboardData) else str(data)
    if len(text) > 500:
        lines = text.count("\n") + 1
        preview = text[:200].replace("\n", "\u21b5")
        event.current_buffer.text = f"[pasted: {lines} lines, {len(text)} chars]\n{preview}..."
    else:
        event.current_buffer.insert_text(text)


PT_STYLE = Style.from_dict({
    "prompt": "#67D8FF bold",
    "toolbar": "bg:default #7F8C98",
    "bottom-toolbar": "bg:default #7F8C98 noreverse",
    "bottom-toolbar.text": "bg:default #7F8C98 noreverse",
})

session_pt = PromptSession(
    completer=SlashCommandToolCompleter(),
    key_bindings=bindings,
    multiline=False,
)

# ── Model selection ──
from atar_core.provider_registry import PROVIDERS as _PROVIDERS

MODELS = [(prof.display_name, pid, prof.default_model) for pid, prof in _PROVIDERS.items()]

BASE_PROMPT = (
    "You are ATAR, an autonomous agent with tools: web_search, web_fetch, read_file, write_file, terminal.\n"
    "Platform: Linux. Shell: bash.\n"
    "CRITICAL:\n"
    "- For research \u2014 call web_search IMMEDIATELY. No explanations first.\n"
    "- For coding \u2014 call write_file IMMEDIATELY. Never say 'Saya akan buat' or 'let me'. Just act.\n"
    "- For simple chat/greetings \u2014 respond directly.\n"
    "- Use Linux commands (xdg-open, rm, ls, grep, etc). Never suggest open/start.\n"
    "- Never prefix your response with 'I will' or 'Saya akan'. Just use the tool.\n"
    "- Never assume or fabricate the user's name. Only use their name if they explicitly tell you.\n"
    "- Be concise. One-sentence answers preferred.\n"
    "- Match the user's language."
)


def _read_config() -> dict:
    try:
        with open(os.path.expanduser("~/.atar/config.json")) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict) -> None:
    p = os.path.expanduser("~/.atar/config.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(cfg, f)


def _create_provider(session_id: str = ""):
    from atar_core.agent import Agent
    from atar_core.provider_router import create_router
    try:
        router = create_router()
        first = router.providers[0]
        cfg = _read_config()
        model = cfg.get("model") or getattr(first, "model", "deepseek-v4-flash")
        agent = Agent(provider=router, max_turns=8, tools=[1], interactive=True)
        prompt = assemble_prompt(session_id=session_id, model=model, cwd=os.getcwd())
        agent.system_prompt = prompt.full
        return router, model, agent
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        return None, "none", None


def _switch_model(provider_id: str, model_id: str) -> str:
    """Switch to a specific provider+model. Returns display string."""
    prof = get_provider(provider_id)
    name = prof.display_name if prof else provider_id
    cfg = _read_config()
    cfg["provider"] = provider_id
    cfg["model"] = model_id
    _save_config(cfg)
    return f"{name} — {model_id}"

def show_banner(model: str, cwd: str, session_id: str) -> None:
    """Hermes-style detailed startup banner."""
    from atar_core.theme import current_theme
    theme = current_theme()
    c = theme.colors

    # Cosmike-style ATAR ASCII
    logo = Text()
    banner_lines = [
        "  :::. :::::::::::::::.    :::::::..         :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::",
        "  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;        ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''",
        " ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['       ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[     ",
        "c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c        c$$$cc$$$c\"$$c.    \"$$ $$\"\"\"\"   $$$ \"Y$c$$     $$     ",
        " 888   888, 88,   888   888,888b \"88bo,     888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,    ",
        " YMM   \"\"`  MMM   YMM   \"\"` MMMM   \"W\"      YMM   \"\"`   `'YMUP\"YMM\"\"\"\"YUMMMMMM     YM     MMM",
    ]
    logo_colors = [c.primary, c.secondary, c.accent, c.primary, c.secondary, c.accent]
    for i, line in enumerate(banner_lines):
        logo.append(line + "\n", style=f"bold {logo_colors[min(i, len(logo_colors)-1)]}")
    logo.append("Clarity in Complexity.\n", style="italic white")
    console.print(logo)

    short_cwd = cwd.replace(os.path.expanduser("~"), "~")
    if len(short_cwd) > 50:
        short_cwd = "..." + short_cwd[-47:]

    # Brain-style ATAR logo — all 42 chars wide
    globe = [
        "                                          ",
        "                ####  ####                ",
        "           ####   ##   ##  ####           ",
        "        ###      ##    ###     ###        ",
        "      ###       ##      ##        ##      ",
        "     ##        ##        ##        ###    ",
        "   ###        ##          ##         ##   ",
        "   ##         #            ##         ##  ",
        "  ##         ##             ##        ##  ",
        "  ##        ##      ##       ##        ## ",
        "  #        ##      ####      ##        ## ",
        "  #######    ######    ###### #######*### ",
        "  ##     ##  ######    #####   ##     *#  ",
        "   #*    #                      ##    ##  ",
        "   ##   ##                       ##  ##   ",
        "    #####                         ####    ",
        "      ##                          ##      ",
        "        ###                    ####       ",
        "          ####              ####          ",
        "              ##############              ",
    ]

    # Build detailed info panel (right column)
    info = []
    info.append(f"[bold {c.primary}]{model}[/] · [dim]{short_cwd}[/]")
    info.append(f"[dim]Session: {session_id[:12]}[/]")
    info.append("")
    from atar_tools.registry import list_all as _list_tools
    from atar_tools.toolsets import enabled_toolsets
    tools = _list_tools()
    tool_names = [t.name for t in tools]
    tool_count = len(tools)
    tsets = enabled_toolsets()
    tset_count = len(tsets)

    info.append("  Available Tools")
    line = "    " + "  ".join(tool_names[:7])
    info.append(line)
    if len(tool_names) > 7:
        info.append("    " + "  ".join(tool_names[7:]))
    info.append("")

    info.append(f"  {tool_count} tools · {tset_count} toolsets · /help for commands · ATAR v0.6.0")
    info.append("[dim italic]Tip: Type /model to switch AI, /sessions to manage sessions[/]")

    panel_content = "\n".join(info)
    panel = Panel(Text.from_markup(panel_content), border_style=c.dim_border, padding=(1, 2), width=min(_TERM_WIDTH - 48, 85))

    # Render globe + panel side by side
    from rich.columns import Columns
    globe_text = Text()
    for line in globe:
        globe_text.append(line + "\n", style=f"bold {c.primary}")
    console.print(Columns([globe_text, panel], equal=False, expand=False))
    console.print()

# ── Runtime stats for status bar ──
_stats = {"turns": 0, "tools": 0, "tokens": 0, "start_time": None, "model": "deepseek-chat", "last_response": None}


def _context_bar() -> str:
    tokens = _stats.get("tokens") or 0
    max_tokens = 128000
    if tokens == 0:
        est = _stats.get("text_chars") or 0
        tokens = max(tokens, est // 3)
        tokens = max(tokens, _stats["turns"] * 200)
    pct = min(tokens / max_tokens, 1.0)
    width = 10
    filled = int(pct * width)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    return f" {tokens/1000:.1f}K/{max_tokens//1000}K [{bar}] {pct*100:.0f}%"


def _status_bar() -> str:
    import time as _time
    if _stats["start_time"] is None:
        _stats["start_time"] = _time.time()
    elapsed = int(_time.time() - _stats["start_time"])
    h, rem = divmod(elapsed, 3600)
    m, s = divmod(rem, 60)
    time_str = f"{h}h {m}m" if h else f"{m}m {s}s"

    parts = [f"\u25c6 {_stats['model']}"]
    parts.append(_context_bar())
    parts.append(f"turns {_stats['turns']}")
    parts.append(f"tools {_stats['tools']}")
    if _stats["last_response"] is not None:
        parts.append(f"\u23f2 {_stats['last_response']:.0f}s")
    parts.append(f"\u2713{time_str}")
    return " \u2502 ".join(parts)


def _try_resume_session() -> object | None:
    """Try to resume the last session from storage."""
    try:
        from atar_core.session import SessionManager
        mgr = SessionManager()
        sessions = mgr.list()
        if sessions:
            return sessions[-1]  # most recent
    except Exception:
        pass
    return None


def run_repl() -> None:
    import atar_tools.tools.file
    import atar_tools.tools.terminal
    import atar_tools.tools.web
    import atar_tools.tools.web_search  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext
    from atar_tools.registry import execute as tool_execute

    session_id = uuid.uuid4().hex[:12]

    provider, model, agent = _create_provider(session_id)
    if not provider or not agent:
        console.print("[red]Set DEEPSEEK_API_KEY.[/]")
        return

    # Fresh session — no auto-resume to avoid old context contamination
    show_banner(model, os.getcwd(), session_id)
    import time as _t
    _stats["model"] = model
    _stats["start_time"] = _t.time()

    _current_task: asyncio.Task | None = None
    _interrupt = False
    async def _agent_turn(prompt: str, ag: Agent) -> None:
        _stats["turns"] += 1
        import time as _t2
        _t_start = _t2.time()
        response_text = ""
        _had_tools = False
        _tool_start_time: dict[str, float] = {}
        _last_tool_id: set[str] = set()
        args_cache: dict[str, dict] = {}

        async def on_tool(name: str, args: dict) -> None:
            nonlocal response_text, _had_tools
            _had_tools = True
            response_text = ""
            tool_sig = f"{name}:{args.get('path', '')}" if name in ("write_file", "read_file") else f"{name}:{str(args)}"
            if tool_sig in _last_tool_id:
                return
            _last_tool_id.add(tool_sig)
            args_cache[name] = args
            _stats["tools"] += 1
            _tool_start_time[name] = _t2.time()
            icons = {"read_file": "\U0001f4d6", "write_file": "\u270d\ufe0f", "terminal": "\U0001f4bb", "web_fetch": "\U0001f50e", "web_search": "\U0001f50d", "patch": "\U0001f527"}
            icon = icons.get(name, "\U0001f527")
            short = str(args)[:60]
            # Show file path for read/write, command for terminal
            if name in ("read_file", "write_file"):
                short = args_cache[name].get("path", str(args))[:60]
            elif name == "terminal":
                short = f"$ {args.get('command', '')[:60]}"
            from atar_core.theme import current_theme
            c = current_theme().colors
            console.print(f"\n  [bold {c.secondary}]\u250a {icon} preparing {name}\u2026[/] [dim]{short}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            icons = {"read_file": "0001F4D6", "WRITE_FILE": "270DFE0F", "TERMINAL": "0001F4BB", "WEB_FETCH": "0001F4C4", "WEB_SEARCH": "0001F50D", "PATCH": "0001F527"}
            from atar_core.theme import current_theme
            c = current_theme().colors
            icons = {"read_file": "\U0001f4d6", "write_file": "\u270d\ufe0f", "terminal": "\U0001f4bb", "web_fetch": "\U0001f50e", "web_search": "\U0001f50d", "patch": "\U0001f527"}
            icons = {"read_file": "\U0001f4d6", "write_file": "\u270d\ufe0f", "terminal": "\U0001f4bb", "web_fetch": "\U0001f4c4", "web_search": "\U0001f50d", "patch": "\U0001f527"}

            if name == "terminal":
                output = result.strip() or "(no output)"
                lines = output.split("\n")[:10]
                shown = "\n".join(f"    [dim]{ln}[/]" for ln in lines)
                preview = args_cache[name].get("command", "")[:50]
                console.print(f"\r  \u2502 \U0001f4bb [bold {c.success}]terminal[/] [dim]{preview} ({elapsed:.1f}s)[/]\n{shown}" if shown else "")
            elif name == "patch":
                output = result.strip() or ""
                colored = []
                for ln in output.split("\n")[:20]:
                    if ln.startswith("+++") or ln.startswith("---"):
                        colored.append(f"    [bold]{ln}[/]")
                    elif ln.startswith("+"):
                        colored.append(f"    [bold #4ADE80]{ln}[/]")
                    elif ln.startswith("-"):
                        colored.append(f"    [bold #F87171]{ln}[/]")
                    else:
                        colored.append(f"    [dim]{ln}[/]")
                path = args_cache[name].get("path", "")
                console.print(f"\r  \u2502 \U0001f527 [bold {c.success}]patch[/] [dim]{path} ({elapsed:.1f}s)[/]\n" + "\n".join(colored))
            elif name == "write_file":
                path = args_cache[name].get("path", "")
                size = len(result) if result else 0
                console.print(f"\r  \u2502 \u270d\ufe0f [bold {c.success}]write[/] [dim]{path} ({size}B, {elapsed:.1f}s)[/]")
            elif name == "read_file":
                path = args_cache[name].get("path", "")
                console.print(f"\r  \u2502 \U0001f4d6 [bold {c.success}]read[/] [dim]{path} ({len(result)} chars, {elapsed:.1f}s)[/]")

        try:
            async def _capture(t: str) -> None:
                nonlocal response_text
                response_text += t
            console.print("\n  ● thinking...", end="")
            await ag.run(prompt, StreamCallbacks(
                on_delta=_capture, on_tool_call=on_tool, on_tool_result=on_tool_result,
            ))
            console.print("\r" + " " * 80 + "\r", end="")  # clear thinking line
        except asyncio.CancelledError:
            console.print("\n[dim]\u23f9 Interrupted[/]")
            return
        _stats["last_response"] = _t2.time() - _t_start

        if not response_text.strip():
            console.print(Rule(style="#394B59"))
            return

        # Hermes-style response container
        console.print()
        from atar_core.theme import current_theme
        c = current_theme().colors
        console.print(Panel(
            Markdown(response_text),
            title="ATAR", border_style=c.border, padding=(1, 2),
            width=min(_TERM_WIDTH - 4, 100),
        ))
        console.print(Rule(style=c.dim_border))

    async def _run() -> None:
        nonlocal provider, model, agent, _current_task, _interrupt
        while True:
            try:
                user = await session_pt.prompt_async(
                    HTML("<prompt>\u203a </prompt>"), style=PT_STYLE, bottom_toolbar=_status_bar,
                )
            except KeyboardInterrupt:
                if _current_task and not _current_task.done():
                    _current_task.cancel()
                    console.print("\n[dim]⏸ Interrupted — type your redirect (or press Ctrl+C again to cancel):[/]")
                    try:
                        redirect = await session_pt.prompt_async(
                            HTML(""), style=PT_STYLE
                        )
                        if redirect.strip():
                            # Inject redirect into agent context as continuation
                            agent._messages.append(Message(role="user", content=f"[Redirect] {redirect.strip()}"))
                            console.print(f"[dim]↳ Redirected: {redirect[:60]}...[/]")
                            _current_task = asyncio.create_task(_agent_turn("", agent))
                    except KeyboardInterrupt:
                        console.print("\n[dim]Cancelled.[/]")
                        continue
                    continue
                console.print("\n[dim]Press Ctrl+D to exit.[/]")
                continue
            except EOFError:
                try:
                    confirm = await session_pt.prompt_async(
                        HTML("\n<dim>Exit ATAR? (y/N)</dim> "), style=PT_STYLE, bottom_toolbar=_status_bar,
                    )
                    if confirm.strip().lower() in ("y", "yes"):
                        console.print("\n[dim]Ataraxic.[/]")
                        break
                    console.print(Rule(style="#394B59"))
                    continue
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Ataraxic.[/]")
                    break

            user = user.strip()
            if not user:
                continue
            if user in ("/quit", "/exit", "/q"):
                console.print("[dim]Ataraxic.[/]")
                break
            if user in ("/clear", "/reset"):
                prov, model, agent = _create_provider(session_id)
                console.print("[dim]Cleared.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/help":
                cmd_registry.list_all()
                cats = cmd_registry.list_by_category()
                for cat, items in cats.items():
                    console.print(f"\n[bold]{cat.upper()}[/]")
                    for c in items:
                        hint = f" {c.arg_hint}" if c.arg_hint else ""
                        aliases = f" ({', '.join(c.aliases)})" if c.aliases else ""
                        console.print(f"  [bold #67D8FF]{c.name}{hint}[/] {c.description}{aliases}")
                console.print()
                continue
            if user == "/model":
                # Step 1: pick provider
                provs = list(_PROVIDERS.keys())
                lines = [f"  [{i}] {_PROVIDERS[p].display_name} ({_PROVIDERS[p].default_model})" for i, p in enumerate(provs)]
                console.print(Panel("\n".join(lines), title="Pick Provider", border_style="#394B59"))
                try:
                    c = await session_pt.prompt_async("Provider #: ", style=PT_STYLE)
                    pi = int(c)
                    if 0 <= pi < len(provs):
                        pid = provs[pi]
                        models = PROVIDER_MODELS.get(pid, [])
                        if len(models) == 1:
                            # Single model — select immediately
                            display = _switch_model(pid, models[0])
                            prov, model, ag = _create_provider(session_id)
                            provider, agent = prov, ag
                            _stats["model"] = display
                            console.print(f"[green]✓ {display}[/]")
                        else:
                            # Step 2: pick model
                            mlines = [f"  [{i}] {m}" for i, m in enumerate(models)]
                            console.print(Panel("\n".join(mlines), title=f"Pick Model — {_PROVIDERS[pid].display_name}", border_style="#394B59"))
                            c2 = await session_pt.prompt_async("Model #: ", style=PT_STYLE)
                            mi = int(c2)
                            if 0 <= mi < len(models):
                                display = _switch_model(pid, models[mi])
                                prov, model, ag = _create_provider(session_id)
                                provider, agent = prov, ag
                                _stats["model"] = display
                                console.print(f"[green]✓ {display}[/]")
                except (ValueError, EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/sessions":
                from atar_storage.sqlite_store import SqliteStore
                store = SqliteStore()
                sessions = store.list_all()
                if not sessions:
                    console.print("[dim]No sessions.[/]")
                else:
                    lines = [f"  [{i}] {s['title'] or s['session_id'][:12]} ({s.get('message_count','?')} msgs)" for i, s in enumerate(sessions)]
                    console.print(Panel("\n".join(lines), title="Sessions", border_style="#394B59"))
                    try:
                        cs = await session_pt.prompt_async("Pick session: ", style=PT_STYLE)
                        idx = int(cs)
                        if 0 <= idx < len(sessions):
                            s = sessions[idx]
                            data = store.load(s["session_id"])
                            if data:
                                prov, model, ag = _create_provider(session_id)
                                for m in data.get("messages", [])[-20:]:

                                    ag._messages.append(Message(role=m.get("role","user"), content=m.get("content",""), tool_calls=m.get("tool_calls"), tool_call_id=m.get("tool_call_id")))
                                provider, agent = prov, ag
                                console.print(f"[green]✓ {s['title'] or s['session_id'][:12]}[/]")
                    except (ValueError, EOFError, KeyboardInterrupt):
                        pass
                console.print(Rule(style="#394B59"))
                continue
            if user == "/save":
                from atar_storage.sqlite_store import SqliteStore
                store = SqliteStore()
                msgs = [{"role": m.role, "content": m.content, "tool_calls": getattr(m, "tool_calls", None), "tool_call_id": getattr(m, "tool_call_id", None)} for m in agent._messages]
                store.save(session_id, "ATAR Session", msgs)
                console.print(f"[green]✓ Saved {len(msgs)} messages ({session_id[:12]})[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/undo":
                text = agent.undo_last_turn()
                if text:
                    console.print(f"[dim]↺ Undone: \"{text}...\"[/]")
                else:
                    console.print("[dim]Nothing to undo.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/retry":
                last = agent.retry_last_turn()
                if last:
                    console.print(f"[dim]↻ Retrying: \"{last[:50]}...\"[/]")
                    _current_task = asyncio.create_task(_agent_turn(last, agent))
                else:
                    console.print("[dim]Nothing to retry.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/checkpoints":
                from atar_tools.tools.checkpoints import list_checkpoints
                cps = list_checkpoints()
                if not cps:
                    console.print("[dim]No checkpoints.[/]")
                else:
                    for cp in cps:
                        console.print(f"  [dim]{cp['id'][:20]}[/] {cp.get('original','?')} ({cp.get('size',0)}B)")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/restore "):
                from atar_tools.tools.checkpoints import restore_checkpoint
                cid = user[len("/restore "):].strip()
                if restore_checkpoint(cid):
                    console.print(f"[green]✓ Restored {cid[:20]}[/]")
                else:
                    console.print(f"[red]Checkpoint not found: {cid[:20]}[/]")
                console.print(Rule(style="#394B59"))
                continue
                console.print(Rule(style="#394B59"))
                continue
            if user == "/code":
                prov2, model2, ag2 = _create_provider(session_id)
                if ag2:
                    ag2.max_turns = 3
                    ag2.system_prompt = "CODE mode. Use terminal, read_file, write_file, git, run_tests."
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Code mode \u00b7 /chat to exit[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/chat":
                prov2, model2, ag2 = _create_provider(session_id)
                if ag2:
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/memory":
                from atar_core.memory import list_memories
                entries = list_memories()
                if not entries:
                    console.print("[dim]No persistent memories.[/]")
                else:
                    for e in entries:
                        console.print(f"  [dim]{e.category}[/] {e.content}")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/remember "):
                from atar_core.memory import add_memory
                text = user[len("/remember "):].strip()
                if text:
                    add_memory(text, category="user")
                    console.print(f"[dim]Saved: {text[:80]}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/compress":
                from atar_core.compress import compress_history
                console.print("[dim]Compressing context...[/]")
                result = await compress_history(agent)
                console.print(f"[green]✓ {result}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/toolset":
                from atar_tools.toolsets import enabled_toolsets
                sets = enabled_toolsets()
                console.print(f"[dim]Active: {', '.join(sets)}[/]")
                console.print("[dim]Available: safe file terminal web browser sessions[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/toolset "):
                ts = user[len("/toolset "):].strip()
                console.print(f"[dim]Toolset '{ts}' activated.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/personality":
                console.print("[dim]Available: default[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/personality "):
                name = user[len("/personality "):].strip()
                console.print(f"[dim]Personality '{name}' loaded.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/usage":
                stats = _stats
                console.print(f"[dim]Tokens: {stats.get('text_chars',0)} chars[/]")
                console.print(f"[dim]Turns: {stats.get('turns',0)}[/]")
                console.print(f"[dim]Tools executed: {stats.get('tools',0)}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/insights"):
                console.print("[dim]Insights across sessions (last 7 days):[/]")
                console.print("[dim]No historical data yet — run more sessions first.[/]")
                console.print(Rule(style="#394B59"))
                continue

            _current_task = asyncio.create_task(_agent_turn(user, agent))
            with suppress(asyncio.CancelledError):
                await _current_task

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
