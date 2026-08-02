"""ATAR CLI — Hermes-style Rich REPL with streaming, tools, sessions, model switching."""

from __future__ import annotations

import asyncio
import json
import os
import re
import uuid

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()
session_pt = PromptSession(
    completer=WordCompleter(
        ["/help", "/model", "/sessions", "/code", "/chat", "/clear", "/quit", "/exit", "/q", "/status", "/tools", "/reset"],
        sentence=True,
        meta_dict={
            "/help": "Commands", "/model": "Switch model", "/sessions": "Sessions",
            "/code": "Code mode", "/chat": "Chat mode", "/clear": "Reset",
            "/quit": "Exit", "/exit": "Exit", "/q": "Quit",
            "/status": "Status", "/tools": "Tools", "/reset": "Reset",
        },
    ),
)

PT_STYLE = Style.from_dict({"prompt": "#4FC3F7 bold", "separator": "#0288D1"})

MODELS = [
    ("DeepSeek V3", "deepseek", "deepseek-chat", "https://api.deepseek.com/v1"),
    ("DeepSeek V4", "deepseek", "deepseek-v4-pro", "https://api.deepseek.com/anthropic"),
    ("OpenAI", "openai", "gpt-4o", "https://api.openai.com/v1"),
    ("Anthropic", "anthropic", "claude-sonnet-4-20250514", "https://api.anthropic.com"),
    ("OpenRouter", "openrouter", "deepseek/deepseek-chat", "https://openrouter.ai/api/v1"),
]

BASE_PROMPT = (
    "You are ATAR. You have tools: web_search, web_fetch, read_file, write_file, terminal.\n"
    "RULES:\n"
    "- For ANY research/reference/lookup request, you MUST call web_search first.\n"
    "- Never say 'I will search' — just call the tool.\n"
    "- Never fabricate URLs, citations, or facts without tool results.\n"
    "- After search, use web_fetch to read top results.\n"
    "- For simple greetings, respond directly without tools.\n"
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


def _create_provider() -> tuple:
    """Create provider + agent from config. Returns (provider, model_name, agent)."""
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
    agent = Agent(provider=provider, max_turns=5, tools=[1])  # enable tool loop
    agent.system_prompt = BASE_PROMPT
    return provider, model, agent


def _switch_model(idx: int) -> str:
    """Switch to model by index. Returns display name."""
    name, prov, model, url = MODELS[idx]
    cfg = _read_config()
    cfg["provider"] = prov
    cfg["model"] = model
    cfg["base_url"] = url
    _save_config(cfg)
    return f"{name} — {model}"


def show_banner(model: str, cwd: str, session_id: str) -> None:
    info = Table.grid(padding=(0, 1))
    info.add_column(style="bold #4FC3F7", justify="left")
    info.add_column(style="dim", justify="left")
    info.add_row(model, "DeepSeek")
    info.add_row("", "")
    info.add_row("Session:", session_id)
    info.add_row("CWD:", cwd)
    info.add_row("", "")
    info.add_row("Tools:", "read_file write_file terminal web_fetch git run_tests")
    info.add_row("", "/help for commands")

    layout = Table.grid(padding=(0, 2))
    layout.add_column(justify="left", width=50)
    layout.add_column(justify="left")

    for i, line in enumerate([
        " █████╗ ████████╗ █████╗ ██████╗",
        "██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗",
        "███████║   ██║   ███████║██████╔╝",
        "██╔══██║   ██║   ██╔══██║██╔══██╗",
        "██║  ██║   ██║   ██║  ██║██║  ██║",
        "╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
    ]):
        layout.add_row(Text(line, style=f"bold {['#4FC3F7','#29B6F6','#0288D1','#0277BD','#01579B','#01579B'][i]}"))

    layout.add_row(Text("\nCLARITY IN COMPLEXITY", style="bold #4FC3F7"),
                   Panel(info, border_style="#0288D1", padding=(1, 2)))
    console.print(Panel(layout, border_style="#0288D1", padding=(1, 2)))
    console.print(Text("  /quit · /clear · /code · /chat · /help", style="dim #4FC3F7"))
    console.print(Rule(style="#0288D1"))


def run_repl() -> None:
    import atar_tools.tools.file  # noqa: F401
    import atar_tools.tools.terminal  # noqa: F401
    import atar_tools.tools.web  # noqa: F401
    import atar_tools.tools.web_search  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext
    from atar_tools.registry import execute as tool_execute

    provider, model, agent = _create_provider()
    if not provider or not agent:
        console.print("[red]Set DEEPSEEK_API_KEY or run atar setup.[/]")
        return

    session_id = uuid.uuid4().hex[:12]
    show_banner(model, os.getcwd(), session_id)

    async def _agent_turn(prompt: str, ag: Agent) -> None:
        ag.state.force("idle")
        response_text = ""

        async def delta(t: str) -> None:
            nonlocal response_text
            response_text += t
            console.print(t, end="", markup=False)

        async def on_tool(name: str, args: dict) -> None:
            icons = {"read_file": "📖", "write_file": "✍️", "terminal": "💻", "web_fetch": "🔎"}
            icon = icons.get(name, "🔧")
            console.print(f"\n  [bold #7C3AED]{icon} {name}[/] [dim]{str(args)[:80]}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            preview = result[:200].replace("\n", " ")
            emoji = "✓" if result else "✗"
            console.print(f"\n  [bold #4CAF50]{emoji} {name}[/] [dim]{preview}[/]")

        console.print(Rule(style="#0288D1"))
        await ag.run(prompt, StreamCallbacks(on_delta=delta, on_tool_call=on_tool, on_tool_result=on_tool_result))
        console.print()
        console.print(Rule(style="#0288D1"))

        if not response_text:
            console.print(Rule(style="#0288D1"))
            return

        # Extract bash commands — text already streamed
        cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
        cmds = [c.strip() for c in cmds if c.strip()]
        if cmds:
            console.print(Panel(
                "\n".join(f"[dim]$[/] [bold #4FC3F7]{c[:150]}[/]" for c in cmds),
                title="Proposed Commands", border_style="#FFD700"))
            try:
                answer = await session_pt.prompt_async(HTML("<yellow>Run? (y/n)</yellow> <dim>[n]</dim> "), style=PT_STYLE)
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer.strip().lower() in ("y", "yes"):
                for c in cmds:
                    tr = await tool_execute("terminal", {"command": c}, ToolContext(metadata={"approved": True}))
                    console.print(Panel(
                        tr.output[:500] if tr.success else f"[red]{tr.error}[/]",
                        title=f"$ {c[:80]}",
                        border_style="#4CAF50" if tr.success else "#F44336"))
            else:
                console.print("[dim][Rejected][/]")
        console.print(Rule(style="#0288D1"))

    async def _run() -> None:
        nonlocal provider, model, agent
        while True:
            try:
                user = await session_pt.prompt_async(HTML("<prompt>· </prompt>"), style=PT_STYLE)
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
                console.print("[dim][Cleared][/]")
                console.print(Rule(style="#0288D1"))
                continue
            if user == "/help":
                console.print(Panel(
                    "/code  coding mode · /chat  chat mode\n"
                    "/model  switch AI model · /sessions  manage\n"
                    "/clear  reset · /quit  exit",
                    title="Commands", border_style="#4FC3F7"))
                continue
            if user == "/model":
                lines_m = []
                for i, (name, _prov, mod, _url) in enumerate(MODELS):
                    m = "▸" if i == 0 else " "
                    lines_m.append(f" {m} [{i}] {name} — {mod}")
                console.print(Panel("\n".join(lines_m), title="📡 Switch Model", border_style="#FFD700"))
                try:
                    c = await session_pt.prompt_async("Pick model number: ", style=PT_STYLE)
                    idx = int(c)
                    if 0 <= idx < len(MODELS):
                        display = _switch_model(idx)
                        prov, model, ag = _create_provider()
                        provider, agent = prov, ag  # update outer scope
                        console.print(f"[green]✓ Switched to {display}[/]")
                except (ValueError, EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#0288D1"))
                continue
            if user == "/sessions":
                from atar_core.session import SessionManager
                mgr = SessionManager()
                sessions = mgr.list()
                if not sessions:
                    console.print("[dim]No sessions.[/]")
                else:
                    lines_s = [f" [{i}] {s.title or s.session_id[:12]}" for i, s in enumerate(sessions)]
                    console.print(Panel("\n".join(lines_s), title="📂 Sessions", border_style="#FFD700"))
                    try:
                        cs = await session_pt.prompt_async("Pick session: ", style=PT_STYLE)
                        idx = int(cs)
                        if 0 <= idx < len(sessions):
                            s = sessions[idx]
                            prov, model, ag = _create_provider()
                            for m in getattr(s, "messages", [])[-20:]:
                                ag._messages.append(m)
                            provider, agent = prov, ag
                            console.print(f"[green]✓ Session: {s.title or s.session_id[:12]}[/]")
                    except (ValueError, EOFError, KeyboardInterrupt):
                        console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#0288D1"))
                continue
            if user == "/code":
                prov2, model2, ag2 = _create_provider()
                if ag2:
                    ag2.max_turns = 3
                    ag2.tools = [1]
                    ag2.system_prompt = "CODE mode. Use terminal, read_file, write_file, git, run_tests."
                    provider, model, agent = prov2, model2, ag2
                console.print(Panel("[bold]Code mode[/] · /chat to exit", border_style="#4CAF50"))
                console.print(Rule(style="#0288D1"))
                continue
            if user == "/chat":
                prov2, model2, ag2 = _create_provider()
                if ag2:
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#0288D1"))
                continue
            await _agent_turn(user, agent)

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
