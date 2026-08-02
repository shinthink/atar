"""ATAR CLI — full Hermes-style with info banner, tool panels, streaming progress."""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
import uuid

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()
session_pt = PromptSession()

PT_STYLE = Style.from_dict({
    "prompt": "#4FC3F7 bold",
    "separator": "#0288D1",
})

BASE_PROMPT = (
    "You are ATAR, a terminal AI agent. When asked to create files, run commands, "
    "or modify the system, you MUST propose a single bash command in a ```bash block. "
    "Never describe — always offer to execute. Keep responses short."
)


def show_banner(model: str, cwd: str, session_id: str) -> None:
    """Hermes-style info banner with model, session, tools."""
    logo = [
        " █████╗ ████████╗ █████╗ ██████╗ ·  █████╗  ██████╗ ███████╗███╗  ██╗████████╗",
        "██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗   ██╔══██╗██╔════╝ ██╔════╝████╗ ██║╚══██╔══╝",
        "███████║   ██║   ███████║██████╔╝   ███████║██║  ███╗█████╗  ██╔██╗██║   ██║",
        "██╔══██║   ██║   ██╔══██║██╔══██╗   ██╔══██║██║   ██║██╔══╝  ██║╚████║   ██║",
        "██║  ██║   ██║   ██║  ██║██║  ██║   ██║  ██║╚██████╔╝███████╗██║ ╚███║   ██║",
        "╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚══╝   ╚═╝",
    ]
    colors = ["#4FC3F7", "#29B6F6", "#0288D1", "#0277BD", "#01579B", "#01579B"]
    logo_text = Text()
    for i, line in enumerate(logo):
        logo_text.append(Text(line + "\n", style=f"bold {colors[i]}"))

    info = Table.grid(padding=(0, 2))
    info.add_column(justify="left")
    info.add_column(justify="left")
    info.add_row(Text(f"{model} · DeepSeek", style="bold #4FC3F7"), Text(f"Session: {session_id}", style="dim"))
    info.add_row(Text(cwd, style="dim"), Text("/help for commands", style="dim"))

    banner_content = Group(logo_text, Text(""), info, Text(""))
    console.print(Panel(banner_content, border_style="#0288D1", padding=(1, 3)))
    console.print(Text("  /quit · /clear · /code · /chat · /help", style="dim #4FC3F7"))
    console.print(Rule(style="#0288D1"))


def run_repl() -> None:
    import atar_tools.tools.terminal  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext
    from atar_provider_anthropic.client import AnthropicProvider
    from atar_tools.registry import execute as tool_execute

    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
    if not key:
        console.print("[red]Set DEEPSEEK_API_KEY.[/]")
        return

    provider = AnthropicProvider(
        api_key=key, base_url="https://api.deepseek.com/anthropic",
        model="deepseek-v4-pro",
    )
    agent = Agent(provider=provider, max_turns=1)
    agent.system_prompt = BASE_PROMPT
    session_id = uuid.uuid4().hex[:12]
    last_elapsed = 0

    show_banner("deepseek-v4-pro", os.getcwd(), session_id)

    async def _agent_turn(prompt: str, ag: Agent) -> None:
        nonlocal last_elapsed
        ag.state.force("idle")
        response_text = ""
        start_time = time.time()

        async def delta(t: str) -> None:
            nonlocal response_text
            response_text += t

        with console.status("[#4FC3F7]Initializing agent...[/]", spinner="dots"):
            await ag.run(prompt, StreamCallbacks(on_delta=delta))

        elapsed = time.time() - start_time
        last_elapsed = int(elapsed)  # update outer scope
        console.print(Rule(style="#0288D1"))

        if not response_text:
            console.print(Rule(style="#0288D1"))
            return

        # Render with Obsidian-style code blocks
        _render_obsidian(response_text)

        # Extract bash
        cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
        cmds = [c.strip() for c in cmds if c.strip()]

        if cmds:
            console.print(Panel(
                "\n".join(f"[dim]$[/] [bold #4FC3F7]{c[:150]}[/]" for c in cmds),
                title="Proposed Commands",
                border_style="#FFD700",
            ))
            try:
                answer = await session_pt.prompt_async(
                    HTML("<yellow>Run? (y/n)</yellow> <dim>[n]</dim> "),
                    style=PT_STYLE,
                )
            except (EOFError, KeyboardInterrupt):
                answer = "n"

            if answer.strip().lower() in ("y", "yes"):
                for c in cmds:
                    tr = await tool_execute(
                        "terminal", {"command": c},
                        ToolContext(metadata={"approved": True}),
                    )
                    console.print(Panel(
                        tr.output[:500] if tr.success else f"[red]{tr.error}[/]",
                        title=f"$ {c[:80]}",
                        border_style="#4CAF50" if tr.success else "#F44336",
                    ))
            else:
                console.print("[dim][Rejected][/]")

        # Footer — just rule, status bar handles timing
        console.print(Rule(style="#0288D1"))


    def _render_obsidian(text: str) -> None:
        """Render text: code blocks in Obsidian panels, rest as markdown."""
        lines = text.strip().split("\n")
        in_code, lang, buf = False, "", []

        for line in lines:
            s = line.strip()
            if s.startswith("```") and not in_code:
                if buf: console.print(Markdown("\n".join(buf))); buf = []
                in_code, lang = True, s[3:].strip() or "code"
                continue
            if s.startswith("```") and in_code:
                in_code = False
                code = "\n".join(buf); buf = []
                console.print(Panel(
                    code, title=f"  {lang}",
                    border_style="#7C3AED" if lang in ("bash","sh","shell") else "#4FC3F7",
                    padding=(1, 2),
                ))
                continue
            buf.append(line)

        if buf:
            console.print(Markdown("\n".join(buf)))


    async def _run() -> None:
        nonlocal agent
        session_start = time.time()
        last_elapsed = 0

        while True:
            # Status bar before prompt
            elapsed = int(time.time() - session_start)
            mins = elapsed // 60
            secs = elapsed % 60
            status = f"deepseek-v4-pro · {mins}m {secs}s · last {last_elapsed}s"
            # Write status at bottom using ANSI
            sys.stderr.write(f"\033]0;ATAR | {status}\007")
            console.print(Text(status, style="dim #4FC3F7"), end="")

            try:
                user = await session_pt.prompt_async(
                    HTML("<prompt>· </prompt>"), style=PT_STYLE,
                )
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Ataraxic.[/]")
                break

            user = user.strip()
            if not user: continue
            if user in ("/quit", "/exit", "/q"):
                console.print("[dim]Ataraxic.[/]"); break
            if user in ("/clear", "/reset"):
                agent = Agent(provider=provider, max_turns=1)
                agent.system_prompt = BASE_PROMPT
                console.print("[dim][Cleared][/]")
                console.print(Rule(style="#0288D1")); continue
            if user == "/help":
                console.print(Panel(
                    "/code  coding mode · /chat  chat mode\n/clear  reset · /quit  exit",
                    title="Commands", border_style="#4FC3F7",
                )); continue
            if user == "/code":
                import atar_tools.tools.file
                import atar_tools.tools.git
                import atar_tools.tools.test_runner  # noqa: F401
                agent = Agent(provider=provider, max_turns=3, tools=[1])
                agent.system_prompt = "You are ATAR in CODE mode. Use terminal, read_file, write_file, git, run_tests. Always propose bash commands."
                console.print(Panel("[bold]Code mode[/] · /chat to exit", border_style="#4CAF50"))
                console.print(Rule(style="#0288D1")); continue
            if user == "/chat":
                agent = Agent(provider=provider, max_turns=1)
                agent.system_prompt = BASE_PROMPT
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#0288D1")); continue

            await _agent_turn(user, agent)

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
