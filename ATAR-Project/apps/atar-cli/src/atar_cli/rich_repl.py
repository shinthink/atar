"""ATAR Classic REPL — compact, autonomous, prompt_toolkit + Rich."""

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

# ── Keybindings ──
class ATARCompleter(Completer):
    """Custom completer for slash commands — matches / prefix."""
    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor.lstrip()
        if not text:
            return
        for cmd in SLASH_COMMANDS:
            if cmd.startswith(text) or cmd.startswith("/" + text):
                yield Completion(cmd, start_position=-len(text), display=cmd)
        for meta_cmd, desc in SLASH_META.items():
            if meta_cmd.startswith(text) or meta_cmd.startswith("/" + text):
                yield Completion(meta_cmd, start_position=-len(text), display=f"{meta_cmd}  ({desc})")


bindings = KeyBindings()


@bindings.add("escape", "enter")
def _(event):
    """Alt+Enter: insert newline."""
    event.current_buffer.insert_text("\n")


@bindings.add("c-c")
def _(event):
    """Ctrl+C: clear buffer for interrupt."""
    event.current_buffer.text = ""


# ── Paste handler — preview large pastes ──
_paste_buffer = ""


@bindings.add("c-v")
def _(event):
    """Ctrl+V: bracketed paste with preview for large content."""
    data = event.app.clipboard.get_data()
    text = data.text if isinstance(data, ClipboardData) else str(data)
    if len(text) > 500:
        lines = text.count("\n") + 1
        preview = text[:200].replace("\n", "↵")
        event.app.current_buffer.text = (
            f"[pasted: {lines} lines, {len(text)} chars — Enter to send]\n{preview}..."
        )
    else:
        event.current_buffer.insert_text(text)

# ── Slash completions ──
SLASH_COMMANDS = [
    "/help", "/model", "/sessions", "/code", "/chat",
    "/clear", "/quit", "/exit", "/q", "/status", "/tools",
]
SLASH_META = {
    "/help": "Commands", "/model": "Switch model", "/sessions": "Sessions",
    "/code": "Code mode", "/chat": "Chat mode", "/clear": "Reset",
    "/quit": "Exit", "/exit": "Exit", "/q": "Quit",
    "/status": "Status", "/tools": "Tools",
}

session_pt = PromptSession(
    completer=ATARCompleter(),
    key_bindings=bindings,
    multiline=False,
    enable_history_search=True,
)

PT_STYLE = Style.from_dict({
    "prompt": "#67D8FF bold",
    "toolbar": "bg:#1a1a2e #7F8C98",
})

MODELS = [
    ("DeepSeek V3", "deepseek", "deepseek-chat"),
    ("DeepSeek V4", "deepseek", "deepseek-v4-pro"),
    ("OpenAI", "openai", "gpt-4o"),
    ("Anthropic", "anthropic", "claude-sonnet-4-20250514"),
    ("OpenRouter", "openrouter", "deepseek/deepseek-chat"),
]

BASE_PROMPT = (
    "You are ATAR, an autonomous agent with tools: web_search, web_fetch, read_file, write_file, terminal.\n"
    "Platform: Linux. Shell: bash.\n"
    "CRITICAL:\n"
    "- For research — call web_search IMMEDIATELY. No explanations first.\n"
    "- For coding — call write_file IMMEDIATELY. Never say 'Saya akan buat' or 'let me'. Just act.\n"
    "- For simple chat/greetings — respond directly.\n"
    "- Use Linux commands (xdg-open, rm, ls, grep, etc). Never suggest open/start.\n"
    "- Never prefix your response with 'I will' or 'Saya akan'. Just use the tool.\n"
    "- Be concise. One-sentence answers preferred.\n"
    "- Match the user's language — if they speak Indonesian, reply in Indonesian. If English, reply in English. Same for any language."
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
        agent.system_prompt = BASE_PROMPT.replace("Platform: Linux", f"Platform: Linux. CWD: {os.getcwd()}")
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
    return f"{name} — {model}"


def show_banner(model: str, cwd: str, session_id: str) -> None:
    """Compact Cosmike-style ASCII banner."""
    from atar_core.theme import current_theme
    theme = current_theme()
    c = theme.colors

    logo = Text()
    logo_colors = [c.primary, c.secondary, c.accent, c.primary, c.secondary, c.accent]
    # Cosmike-style smooth banner
    banner_lines = [
        "    ╭─── ∘ ∘ ∘ ∘ ───╮",
        "   ∘   █████╗ ████████╗   ∘",
        "   ∘  ██╔══██╗╚══██╔══╝  ∘",
        "   ·  ███████║   ██║     ·",
        "   ·  ██╔══██║   ██║     ·",
        "   ∘  ██║  ██║   ██║    ∘",
        "   ∘  ╚═╝  ╚═╝   ╚═╝    ∘",
        "    ╰─── · · · · ───╯",
    ]
    for i, line in enumerate(banner_lines):
        style = logo_colors[min(i, len(logo_colors)-1)]
        logo.append(line + "\n", style=f"bold {style}")
    logo.append("Clarity in Complexity.\n\n", style=f"bold {c.primary}")

    short_cwd = cwd.replace(os.path.expanduser("~"), "~")
    if len(short_cwd) > 50:
        short_cwd = "..." + short_cwd[-47:]
    info = Text()
    info.append(f"{model}  ·  ", style=f"bold {c.primary}")
    info.append(f"{short_cwd}  ·  ", style="dim")
    info.append(f"session {session_id[:6]}  ·  ", style="dim")
    info.append("6 tools", style="dim")

    console.print(logo)
    console.print(info)
    console.print(Rule(style=c.dim_border))


# ── Runtime stats for status bar ──
_stats = {"turns": 0, "tools": 0, "tokens": 0, "start_time": None, "model": "deepseek-chat", "last_response": None}


def _context_bar() -> str:
    """Draw ASCII context usage bar. Estimate tokens from text if real count unavailable."""
    tokens = _stats.get("tokens") or 0
    max_tokens = 128000
    if tokens == 0:
        # Estimate from response text length if available
        est = _stats.get("text_chars") or 0
        tokens = max(tokens, est // 3)  # rough: 3 chars per token
        tokens = max(tokens, _stats["turns"] * 200)  # minimum per turn
    pct = min(tokens / max_tokens, 1.0)
    width = 10
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    return f" {tokens/1000:.1f}K/{max_tokens//1000}K [{bar}] {pct*100:.0f}%"


def _status_bar() -> str:
    """Return bottom toolbar with real stats like Hermes."""
    import time as _time
    if _stats["start_time"] is None:
        _stats["start_time"] = _time.time()
    elapsed = int(_time.time() - _stats["start_time"])
    h, rem = divmod(elapsed, 3600)
    m, s = divmod(rem, 60)
    time_str = f"{h}h {m}m" if h else f"{m}m {s}s"

    parts = [f"◆ {_stats['model']}"]
    parts.append(_context_bar())
    parts.append(f"turns {_stats['turns']}")
    parts.append(f"tools {_stats['tools']}")
    if _stats["last_response"] is not None:
        parts.append(f"⏲ {_stats['last_response']:.0f}s")
    parts.append(f"✓{time_str}")
    return " │ ".join(parts)


def run_repl() -> None:
    import atar_tools.tools.file
    import atar_tools.tools.terminal
    import atar_tools.tools.web
    import atar_tools.tools.web_search  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext
    from atar_tools.registry import execute as tool_execute

    provider, model, agent = _create_provider()
    if not provider or not agent:
        console.print("[red]Set DEEPSEEK_API_KEY.[/]")
        return

    session_id = uuid.uuid4().hex[:12]
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
        _tool_start_time: dict[str, float] = {}  # per-tool timing
        _last_tool_id: set[str] = set()  # dedup

        async def delta(t: str) -> None:
            nonlocal response_text
            response_text += t
            _stats["text_chars"] = (_stats.get("text_chars") or 0) + len(t)

        async def on_tool(name: str, args: dict) -> None:
            nonlocal response_text, _had_tools
            _had_tools = True
            response_text = ""  # discard chatter from tool turns

            # Dedup: by path for write/read, by content for others
            tool_sig = f"{name}:{args.get('path', '')}" if name in ("write_file", "read_file") else f"{name}:{str(args)}"
            if tool_sig in _last_tool_id:
                return
            _last_tool_id.add(tool_sig)

            _stats["tools"] += 1
            _tool_start_time[name] = _t2.time()
            icons = {"read_file": "📖", "write_file": "✍️", "terminal": "💻", "web_fetch": "🔎", "web_search": "🔍"}
            icon = icons.get(name, "🔧")
            from atar_core.theme import current_theme
            c = current_theme().colors
            console.print(f"\n  [bold {c.secondary}]┊ ◌ {icon} {name}[/] [dim]{str(args)[:60]}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            elapsed = _t2.time() - _tool_start_time.get(name, _t2.time())
            from atar_core.theme import current_theme
            c = current_theme().colors

            if name == "terminal":
                # Show command output inline
                output = result.strip() or "(no output)"
                lines = output.split("\n")[:10]
                shown = "\n".join(f"    [dim]{ln}[/]" for ln in lines)
                console.print(f"\r  [bold {c.success}]┊ ✓ terminal[/] [dim]({elapsed:.1f}s)[/]\n{shown}" if shown else "")
            else:
                cleaner = {"write_file": "Wrote", "read_file": "Read", "web_search": "Found", "web_fetch": "Fetched"}
                verb = cleaner.get(name, "Done")
                console.print(f"\r  [bold {c.success}]┊ ✓ {verb}[/] [dim]({elapsed:.1f}s)[/]")

        console.print(Rule(style="#394B59"))
        try:
            with console.status("[bold #67D8FF]Thinking...[/]", spinner="dots"):
                await ag.run(prompt, StreamCallbacks(
                    on_delta=delta, on_tool_call=on_tool, on_tool_result=on_tool_result,
                ))
        except asyncio.CancelledError:
            console.print("\n[dim]⏹ Interrupted[/]")
            return
        _stats["last_response"] = _t2.time() - _t_start

        if not response_text.strip():
            console.print(Rule(style="#394B59"))
            return

        # Render final response as Markdown
        console.print()
        console.print(Markdown(response_text))
        console.print(Rule(style="#394B59"))

        # Bash command extraction from raw text
        cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
        cmds = [c.strip() for c in cmds if c.strip()]
        if cmds:
            console.print(Panel(
                "\n".join(f"[dim]$[/] [bold #67D8FF]{c[:150]}[/]" for c in cmds),
                title="Proposed Commands", border_style="#E8C07D"))
            try:
                answer = await session_pt.prompt_async(
                    HTML("<yellow>Run? (y/n)</yellow> <dim>[n]</dim> "), style=PT_STYLE,
                    bottom_toolbar=_status_bar,
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
                    HTML("<prompt>› </prompt>"),
                    style=PT_STYLE,
                    bottom_toolbar=_status_bar,
                )
            except KeyboardInterrupt:
                if _current_task and not _current_task.done():
                    _current_task.cancel()
                    console.print("\n[dim]Interrupted.[/]")
                    continue
                console.print("\n[dim]Press Ctrl+D to exit.[/]")
                continue
            except EOFError:
                # Ctrl+D — confirm before exit
                try:
                    confirm = await session_pt.prompt_async(
                        HTML("\n<dim>Exit ATAR? (y/N)</dim> "),
                        style=PT_STYLE,
                        bottom_toolbar=_status_bar,
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
                console.print("[bold]/help /model /sessions /code /chat /clear /quit[/]")
                continue
            if user == "/model":
                lines = [f"  [{i}] {n} — {m}" for i, (n, _, m) in enumerate(MODELS)]
                console.print(Panel("\n".join(lines), title="Switch Model", border_style="#394B59"))
                try:
                    c = await session_pt.prompt_async("Pick model number: ", style=PT_STYLE, bottom_toolbar=_status_bar)
                    idx = int(c)
                    if 0 <= idx < len(MODELS):
                        display = _switch_model(idx)
                        _stats["model"] = display.split(" — ")[1] if " — " in display else display
                        prov, model, ag = _create_provider()
                        provider, agent = prov, ag
                        console.print(f"[green]✓ {display}[/]")
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
                            console.print(f"[green]✓ {s.title or s.session_id[:12]}[/]")
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
                console.print("[dim]Code mode · /chat to exit[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/chat":
                prov2, model2, ag2 = _create_provider()
                if ag2:
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#394B59"))
                continue

            # Run agent turn
            _current_task = asyncio.create_task(_agent_turn(user, agent))
            with suppress(asyncio.CancelledError):
                await _current_task

    # Remove Ctrl+C signal handler override — let prompt_toolkit handle it
    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
