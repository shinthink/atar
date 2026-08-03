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
from atar_core.commands import register_command, registry as cmd_registry
from atar_core.provider_registry import list_providers, get_provider

# Register all commands
register_command("/help", "Show available commands", aliases=["/h"], category="system")
from atar_core.prompt import assemble as assemble_prompt
register_command("/model", "Switch AI model", category="model", arg_hint="[name]")
register_command("/sessions", "Manage sessions", aliases=["/s"], category="session")
register_command("/code", "Coding mode", category="tools")
register_command("/chat", "Chat mode", category="tools")
register_command("/clear", "Reset conversation", aliases=["/reset"], category="session")
register_command("/quit", "Exit ATAR", aliases=["/exit", "/q"], category="system")
register_command("/status", "Show runtime status", category="system")
register_command("/tools", "List available tools", category="tools")
register_command("/new", "Start a new session (fresh ID + history)", category="session", arg_hint="[name]")
register_command("/title", "Set session title", category="session", arg_hint="[name]")
register_command("/usage", "Show context usage", category="system")
register_command("/save", "Save current conversation", category="session")


# ── Keybindings ──
bindings = KeyBindings()


@bindings.add("escape", "enter")
def _(event):
    event.current_buffer.insert_text("\n")


@bindings.add("tab")
def _(event):
    """Tab: show slash completions via inline menu."""
    b = event.current_buffer
    text = b.text.lstrip()
    cmds = cmd_registry.completions()
    matches = [c for c in cmds if c.startswith(text)]
    if not matches:
        matches = [c for c in cmds if text in c]
    if matches:
        b.text = ""
        console.print()
        lines = []
        for m in matches[:12]:
            cmd = cmd_registry.get(m)
            desc = cmd.description if cmd else ""
            lines.append(f"  [bold #67D8FF]{m}[/]  [dim]{desc}[/]")
        console.print("\n".join(lines) if lines else "[dim]No commands[/]")
        b.text = text
    else:
        b.insert_text("\t")


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


PT_STYLE = Style.from_dict({"prompt": "#67D8FF bold", "toolbar": "bg:#1a1a2e #7F8C98"})

session_pt = PromptSession(
    key_bindings=bindings,
    multiline=False,
)

MODELS = [
    (p.display_name, p.id, p.default_model)
    for p in list_providers()
]

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


def _create_provider():
    from atar_core.agent import Agent
    from atar_core.provider_router import create_router
    try:
        router = create_router()
        first = router.providers[0]
        model = getattr(first, "model", "deepseek-chat")
        agent = Agent(provider=router, max_turns=8, tools=[1])
        prompt = assemble_prompt(session_id=session_id, model=model, cwd=os.getcwd())
        agent.system_prompt = prompt.full
        return router, model, agent
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        return None, "none", None


def _switch_model(idx: int) -> str:
    name, prov, model = MODELS[idx]
    cfg = _read_config()
    cfg["provider"] = prov
    cfg["model"] = model
    _save_config(cfg)
    return f"{name} \u2014 {model}"

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
    tools = _list_tools()
    tool_names = [t.name for t in tools]
    tool_count = len(tools)
    skill_count = 3  # TODO: wire real skill registry

    info.append("  Available Tools")
    line = "    " + "  ".join(tool_names[:7])
    info.append(line)
    if len(tool_names) > 7:
        info.append("    " + "  ".join(tool_names[7:]))
    info.append("")

    info.append(f"  {tool_count} tools · {skill_count} skills · /help for commands · ATAR v0.6.0")
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

    provider, model, agent = _create_provider()
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

        async def on_tool(name: str, args: dict) -> None:
            nonlocal response_text, _had_tools
            _had_tools = True
            response_text = ""
            tool_sig = f"{name}:{args.get('path', '')}" if name in ("write_file", "read_file") else f"{name}:{str(args)}"
            if tool_sig in _last_tool_id:
                return
            _last_tool_id.add(tool_sig)
            _stats["tools"] += 1
            _tool_start_time[name] = _t2.time()
            icons = {"read_file": "\U0001f4d6", "write_file": "\u270d\ufe0f", "terminal": "\U0001f4bb", "web_fetch": "\U0001f50e", "web_search": "\U0001f50d", "patch": "\U0001f527"}
            icon = icons.get(name, "\U0001f527")
            short = str(args)[:60]
            # Show file path for read/write, command for terminal
            if name in ("read_file", "write_file"):
                short = args.get("path", str(args))[:60]
            elif name == "terminal":
                short = f"$ {args.get('command', '')[:60]}"
            from atar_core.theme import current_theme
            c = current_theme().colors
            console.print(f"\n  [bold {c.secondary}]\u250a {icon} preparing {name}\u2026[/] [dim]{short}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            elapsed = _t2.time() - _tool_start_time.get(name, _t2.time())
            from atar_core.theme import current_theme
            c = current_theme().colors
            icons = {"read_file": "\U0001f4d6", "write_file": "\u270d\ufe0f", "terminal": "\U0001f4bb", "web_fetch": "\U0001f50e", "web_search": "\U0001f50d", "patch": "\U0001f527"}
            icon = icons.get(name, "\U0001f527")

            if name == "terminal":
                output = result.strip() or "(no output)"
                lines = output.split("\n")[:10]
                shown = "\n".join(f"    [dim]{ln}[/]" for ln in lines)
                console.print(f"\r  [bold {c.success}]\u2502 {icon} {name}[/] [dim]({elapsed:.1f}s)[/]\n{shown}" if shown else "")
            elif name in ("read_file", "write_file"):
                size = len(result) if result else 0
                label = f"Wrote {size} bytes" if name == "write_file" else f"Read {len(result)} chars"
                console.print(f"\r  [bold {c.success}]\u2502 {icon} {label}[/] [dim]({elapsed:.1f}s)[/]")
            else:
                cleaner = {"web_search": "Found results", "web_fetch": "Fetched content"}
                verb = cleaner.get(name, "Done")
                console.print(f"\r  [bold {c.success}]\u2502 {icon} {verb}[/] [dim]({elapsed:.1f}s)[/]")

        console.print(Rule(style="#394B59"))
        try:
            with console.status("[bold #67D8FF]\u25cf[/]", spinner="dots") as status:
                async def _stream_progress(t: str) -> None:
                    nonlocal response_text
                    response_text += t
                    _stats["text_chars"] = (_stats.get("text_chars") or 0) + len(t)
                    preview = response_text[:80].replace("\n", " ")
                    if preview:
                        label = f"{preview}..." if len(response_text) > 80 else preview
                        status.update(f"[bold #67D8FF]\u25cf[/] [dim]{label}[/]")
                await ag.run(prompt, StreamCallbacks(
                    on_delta=_stream_progress, on_tool_call=on_tool, on_tool_result=on_tool_result,
                ))
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

        # Bash command extraction
        cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
        cmds = [c.strip() for c in cmds if c.strip()]
        if cmds:
            console.print(Panel(
                "\n".join(f"[dim]$[/] [bold #67D8FF]{c[:150]}[/]" for c in cmds),
                title="Proposed Commands", border_style="#E8C07D"))
            try:
                answer = await session_pt.prompt_async(
                    HTML("<yellow>Run? (y/n)</yellow> <dim>[n]</dim> "), style=PT_STYLE, bottom_toolbar=_status_bar,
                )
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer.strip().lower() in ("y", "yes"):
                for c in cmds:
                    tr = await tool_execute("terminal", {"command": c}, ToolContext(metadata={"approved": True}))
                    console.print(Panel(
                        tr.output[:500] if tr.success else f"[red]{tr.error}[/]",
                        title=f"$ {c[:80]}", border_style="#78D6A5" if tr.success else "#F08C8C"))
            else:
                console.print("[dim][Rejected][/]")

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
                    console.print("\n[dim]Interrupted.[/]")
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
                prov, model, agent = _create_provider()
                console.print("[dim]Cleared.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/help":
                cmds = cmd_registry.list_all()
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
                lines = [f"  [{i}] {n} \u2014 {m}" for i, (n, _, m) in enumerate(MODELS)]
                console.print(Panel("\n".join(lines), title="Switch Model", border_style="#394B59"))
                try:
                    c = await session_pt.prompt_async("Pick model number: ", style=PT_STYLE, bottom_toolbar=_status_bar)
                    idx = int(c)
                    if 0 <= idx < len(MODELS):
                        display = _switch_model(idx)
                        _stats["model"] = display.split(" \u2014 ")[1] if " \u2014 " in display else display
                        prov, model, ag = _create_provider()
                        provider, agent = prov, ag
                        console.print(f"[green]\u2713 {display}[/]")
                except (ValueError, EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/sessions":
                from atar_core.session import SessionManager
                mgr = SessionManager()
                sessions = mgr.list()
                if not sessions:
                    console.print("[dim]No sessions.[/]")
                else:
                    lines = [f"  [{i}] {s.title or s.session_id[:12]}" for i, s in enumerate(sessions)]
                    console.print(Panel("\n".join(lines), title="Sessions", border_style="#394B59"))
                    try:
                        cs = await session_pt.prompt_async("Pick session: ", style=PT_STYLE, bottom_toolbar=_status_bar)
                        idx = int(cs)
                        if 0 <= idx < len(sessions):
                            s = sessions[idx]
                            prov, model, ag = _create_provider()
                            for m in getattr(s, "messages", [])[-20:]:
                                ag._messages.append(m)
                            provider, agent = prov, ag
                            console.print(f"[green]\u2713 {s.title or s.session_id[:12]}[/]")
                    except (ValueError, EOFError, KeyboardInterrupt):
                        console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/code":
                prov2, model2, ag2 = _create_provider()
                if ag2:
                    ag2.max_turns = 3
                    ag2.system_prompt = "CODE mode. Use terminal, read_file, write_file, git, run_tests."
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Code mode \u00b7 /chat to exit[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/chat":
                prov2, model2, ag2 = _create_provider()
                if ag2:
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#394B59"))
                continue

            _current_task = asyncio.create_task(_agent_turn(user, agent))
            with suppress(asyncio.CancelledError):
                await _current_task

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
