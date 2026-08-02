"""ATAR interactive CLI — Hermes-style with Rich UI."""

from __future__ import annotations

import asyncio
import os
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text

console = Console()

BANNER = (
    ":::.,::::::::::::::::.    :::::::..\n"
    "  ;;`;;;;;;;;;;'''';;`;;   ;;;;``;;;;\n"
    " ,[[ '[[,   [[    ,[[ '[[,  [[[,/[[['\n"
    "c$$$cc$$$c  $$   c$$$cc$$$c $$$$$$c\n"
    " 888   888, 88,   888   888,888b \"88bo,\n"
    " YMM   \"\"`  MMM   YMM   \"\"` MMMM   \"W\"\n"
    "  :::.      .,-:::::/ .,:::::::::.    :::.::::::::::::\n"
    "  ;;`;;   ,;;-'````'  ;;;;''''`;;;;,  `;;;;;;;;;;;''''\n"
    " ,[[ '[[, [[[   [[[[[[/[[cccc   [[[[[. '[[     [[\n"
    "c$$$cc$$$c\"$$c.    \"$$ $$\"\"\"\"   $$$ \"Y$c$$     $$\n"
    " 888   888,`Y8bo,,,o88o888oo,__ 888    Y88     88,\n"
    " YMM   \"\"`   `'YMUP\"YMM\"\"\"\"YUMMMMMM     YM     MMM"
)


def show_banner() -> None:
    console.print(Panel(
        Text(BANNER, style="bold cyan", justify="center"),
        border_style="cyan",
        padding=(1, 2),
    ))
    console.print(Text("  CLARITY IN COMPLEXITY", style="bold bright_cyan", justify="center"))
    console.print(Text("  Type /quit to exit  /clear to reset", style="dim", justify="center"))
    console.print(Rule(style="cyan"))


def run_repl() -> None:
    import atar_tools.tools.terminal  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext

    # Get provider
    from atar_provider_anthropic.client import AnthropicProvider
    from atar_tools.registry import execute as tool_execute
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or ""
    if not key:
        console.print("[red]Set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY.[/]")
        return
    provider = AnthropicProvider(
        api_key=key, base_url="https://api.deepseek.com/anthropic",
        model="deepseek-v4-pro",
    )
    agent = Agent(provider=provider, max_turns=1)

    show_banner()

    async def _run() -> None:
        nonlocal agent
        while True:
            try:
                user = Prompt.ask(Text("▸", style="bold cyan"))
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Ataraxic.[/]")
                break

            if not user.strip():
                continue
            if user.strip() in ("/quit", "/exit", "/q"):
                console.print("[dim]Ataraxic.[/]")
                break
            if user.strip() in ("/clear", "/reset"):
                agent = Agent(provider=provider, max_turns=1)
                console.print("[dim][Cleared][/]")
                console.print(Rule(style="cyan"))
                continue

            agent.state.force("idle")

            # Show thinking indicator
            status = console.status("[cyan]Thinking...[/]", spinner="dots")
            status.start()

            response_text = ""

            async def delta(t: str) -> None:
                nonlocal response_text
                response_text += t

            await agent.run(user, StreamCallbacks(on_delta=delta))
            status.stop()

            if not response_text:
                console.print(Rule(style="red"))
                continue

            # Render as markdown
            console.print(Markdown(response_text.strip()), style="")
            console.print()

            # Detect bash commands
            cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
            cmds = [c.strip() for c in cmds if c.strip()]

            if cmds:
                console.print(Panel(
                    "\n".join(f"  ${c}" for c in cmds),
                    title="Proposed commands",
                    border_style="yellow",
                ))
                answer = Prompt.ask(
                    Text("Run? (y/n/e)", style="bold yellow"),
                    choices=["y", "n", "e"], default="n",
                )

                if answer == "y":
                    for c in cmds:
                        tr = await tool_execute(
                            "terminal", {"command": c},
                            ToolContext(metadata={"approved": True}),
                        )
                        console.print(Panel(
                            tr.output[:500] if tr.success else f"[red]{tr.error}[/]",
                            title=f"$ {c[:60]}",
                            border_style="green" if tr.success else "red",
                        ))
                elif answer == "e":
                    new_cmd = Prompt.ask("  $")
                    if new_cmd.strip():
                        tr = await tool_execute(
                            "terminal", {"command": new_cmd.strip()},
                            ToolContext(metadata={"approved": True}),
                        )
                        console.print(Panel(
                            tr.output[:500] if tr.success else f"[red]{tr.error}[/]",
                            border_style="green" if tr.success else "red",
                        ))
                else:
                    console.print("[dim][Rejected][/]")

            console.print(Rule(style="cyan"))

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
