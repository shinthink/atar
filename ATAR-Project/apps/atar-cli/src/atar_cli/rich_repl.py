"""ATAR Classic REPL — compact, autonomous, prompt_toolkit + Rich."""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from contextlib import suppress

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

console = Console()

# ── Keybindings ──
bindings = KeyBindings()

@bindings.add("escape", "enter")
def _(event):
    """Alt+Enter: insert newline."""
    event.current_buffer.insert_text("\n")

@bindings.add("c-c")
def _(event):
    """Ctrl+C: set flag for interrupt, don't kill process."""
    event.app.current_buffer.text = ""

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
    completer=WordCompleter(SLASH_COMMANDS, sentence=True, meta_dict=SLASH_META),
    key_bindings=bindings,
    multiline=False,  # Alt+Enter for newline
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
    "You are ATAR. You have tools: web_search, web_fetch, read_file, write_file, terminal.\n"
    "RULES:\n"
    "- For ANY research/reference/lookup, call web_search first.\n"
    "- Never say 'I will search' — just call the tool.\n"
    "- Never fabricate URLs, citations, or facts.\n"
    "- After search, use web_fetch to read top results.\n"
    "- For simple greetings, respond directly.\n"
    "Be concise. Use Indonesian if the user speaks Indonesian."
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
    from atar_core.config_reader import get_api_key
    from atar_provider_deepseek.client import DeepSeekProvider

    cfg = _read_config()
    prov_id = cfg.get("provider", "deepseek")
    model = cfg.get("model", "deepseek-chat")
    key = get_api_key(prov_id) or os.environ.get("DEEPSEEK_API_KEY") or ""

    if not key:
        return None, model, None
    provider = DeepSeekProvider(api_key=key, model=model)
    agent = Agent(provider=provider, max_turns=5, tools=[1])
    agent.system_prompt = BASE_PROMPT
    return provider, model, agent


def _switch_model(idx: int) -> str:
    name, prov, model = MODELS[idx]
    cfg = _read_config()
    cfg["provider"] = prov
    cfg["model"] = model
    _save_config(cfg)
    return f"{name} — {model}"


def show_banner(model: str, cwd: str, session_id: str) -> None:
    """Compact 8-line banner — no full-width frame."""
    logo = Text()
    for i, line in enumerate([
        " █████╗ ████████╗ █████╗ ██████╗",
        "██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗",
        "███████║   ██║   ███████║██████╔╝",
        "██╔══██║   ██║   ██╔══██║██╔══██╗",
        "██║  ██║   ██║   ██║  ██║██║  ██║",
        "╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
    ]):
        logo.append(line + "\n", style=f"bold {['#67D8FF','#5BC0EB','#4EA8D4','#4290BD','#3678A6','#2A608F'][i]}")
    logo.append("Clarity in Complexity.\n\n", style="bold #67D8FF")

    short_cwd = cwd.replace(os.path.expanduser("~"), "~")
    if len(short_cwd) > 50:
        short_cwd = "..." + short_cwd[-47:]
    info = Text()
    info.append(f"{model}  ·  ", style="bold #67D8FF")
    info.append(f"{short_cwd}  ·  ", style="dim")
    info.append(f"session {session_id[:6]}  ·  ", style="dim")
    info.append("6 tools", style="dim")

    console.print(logo)
    console.print(info)
    console.print(Rule(style="#394B59"))


def _status_bar() -> str:
    """Return bottom toolbar text for prompt_toolkit."""
    cfg = _read_config()
    model = cfg.get("model", "deepseek-chat")
    return f" {model} │ /help for commands │ Ctrl+C interrupt │ Ctrl+D exit "


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

    _current_task: asyncio.Task | None = None
    _interrupt = False

    async def _agent_turn(prompt: str, ag: Agent) -> None:
        nonlocal _interrupt
        response_text = ""

        async def delta(t: str) -> None:
            nonlocal response_text
            response_text += t
            console.print(t, end="", markup=False)

        async def on_tool(name: str, args: dict) -> None:
            icons = {"read_file": "📖", "write_file": "✍️", "terminal": "💻", "web_fetch": "🔎", "web_search": "🔍"}
            icon = icons.get(name, "🔧")
            console.print(f"\n  [bold #7C3AED]┊ {icon} {name}[/] [dim]{str(args)[:60]}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            preview = result[:150].replace("\n", " ")
            console.print(f"\n  [bold #4CAF50]┊ {name}[/] [dim]{preview}[/]")

        console.print(Rule(style="#394B59"))
        try:
            await ag.run(prompt, StreamCallbacks(
                on_delta=delta, on_tool_call=on_tool, on_tool_result=on_tool_result,
            ))
        except asyncio.CancelledError:
            console.print("\n[dim]⏹ Interrupted[/]")
            return
        console.print()
        console.print(Rule(style="#394B59"))

        if not response_text:
            return

        # Bash command extraction
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
