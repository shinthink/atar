"""ATAR CLI — Hermes-style interface with prompt_toolkit + Rich."""

from __future__ import annotations

import asyncio
import os
import re

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

console = Console()
session_pt = PromptSession()

PT_STYLE = Style.from_dict({
    "prompt": "#4FC3F7 bold",
    "separator": "#0288D1",
})

BASE_PROMPT = (
    "You are ATAR, a terminal AI agent. When asked to create files, "
    "run commands, or modify the system, you MUST propose a bash command "
    "in a ```bash code block. Never just describe — always offer to execute. "
    "For file creation use: echo 'content' > path. Keep responses short."
)

CODE_PROMPT = (
    "You are ATAR in CODE mode. You can read, write, and analyze code. "
    "Use terminal for all operations. When making changes, always propose "
    "a ```bash command. Read relevant files before editing. Be precise."
)

HELP_TEXT = (
    "/chat   normal chat mode\n"
    "/code   coding mode (file read/write, git, tests)\n"
    "/clear  reset conversation\n"
    "/quit   exit\n"
    "When agent suggests commands, approve (y/n/e)."
)


def show_banner() -> None:
    """Render the ATAR startup banner — Hermes style."""
    logo_lines = [
        " █████╗ ████████╗ █████╗ ██████╗        █████╗  ██████╗ ███████╗███╗  ██╗████████╗",
        "██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗      ██╔══██╗██╔════╝ ██╔════╝████╗ ██║╚══██╔══╝",
        "███████║   ██║   ███████║██████╔╝█████╗███████║██║  ███╗█████╗  ██╔██╗██║   ██║",
        "██╔══██║   ██║   ██╔══██║██╔══██╗╚════╝██╔══██║██║   ██║██╔══╝  ██║╚████║   ██║",
        "██║  ██║   ██║   ██║  ██║██║  ██║      ██║  ██║╚██████╔╝███████╗██║ ╚███║   ██║",
        "╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝      ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚══╝   ╚═╝",
    ]
    colors = ["#4FC3F7", "#29B6F6", "#0288D1", "#0277BD", "#01579B", "#01579B"]
    logo_text = []
    for i, line in enumerate(logo_lines):
        logo_text.append(Text(line, style=f"bold {colors[i]}"))

    subtitle = Text("CLARITY IN COMPLEXITY  ", style="bold #4FC3F7")
    ataraxia = Text("Ataraxia", style="italic #4FC3F7")
    subtitle.append(Text(" — ", style="dim"))
    subtitle.append(ataraxia)

    inner = Group(
        Text(""),
        *logo_text,
        Text(""),
        subtitle,
    )
    console.print(Panel(inner, border_style="#0288D1", padding=(1, 4)))
    console.print(Text("  /quit   exit    /clear   reset    /help   commands", style="dim #4FC3F7"))
    console.print(Rule(style="#0288D1"))


def build_prompt(session_id: str = "") -> HTML:
    """Build the Hermes-style input prompt."""
    sid = session_id[:8] if session_id else "new"
    return HTML(
        f'<prompt>{sid} ▸ </prompt>'
    )


def run_repl() -> None:
    """Main REPL with Hermes-style interface."""
    import atar_tools.tools.terminal  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext
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
    agent.system_prompt = (
        "You are ATAR, a terminal AI agent. When asked to create files, run commands, "
        "or modify the system, you MUST propose a bash command in a ```bash code block. "
        "Never just describe what to do — always offer to execute. "
        "For file creation use: echo 'content' > path. Keep responses short."
    )

    show_banner()

    async def _agent_turn(prompt: str, ag: Agent, prov) -> None:
        """Multi-turn agent interaction with tool approval loop."""
        ag.state.force("idle")
        response_text = ""

        async def delta(t: str) -> None:
            nonlocal response_text
            response_text += t

        with console.status("[#4FC3F7]Thinking...[/]", spinner="dots"):
            await ag.run(prompt, StreamCallbacks(on_delta=delta))

        if not response_text:
            console.print(Rule(style="#0288D1"))
            return

        # Render: split into code blocks (panels) and text (markdown)
        _render_response(response_text)

        # Extract bash commands
        cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
        cmds = [c.strip() for c in cmds if c.strip()]

        if not cmds:
            console.print(Rule(style="#0288D1"))
            return

        # Show proposed commands
        console.print(Panel(
            "\n".join(f"[dim]$[/] [bold #4FC3F7]{c[:120]}[/]" for c in cmds),
            title="Proposed Commands",
            border_style="#FFD700",
        ))

        try:
            answer = await session_pt.prompt_async(
                HTML("<yellow>Run? (y/n/e)</yellow> <dim>[n]</dim> "),
                style=PT_STYLE,
            )
        except (EOFError, KeyboardInterrupt):
            answer = "n"

        answer = answer.strip().lower()

        if answer in ("y", "yes"):
            for c in cmds:
                tr = await tool_execute(
                    "terminal", {"command": c},
                    ToolContext(metadata={"approved": True}),
                )
                result_text = tr.output[:500] if tr.success else f"[red]{tr.error}[/]"
                console.print(Panel(
                    result_text,
                    title=f"$ {c[:60]}",
                    border_style="#4CAF50" if tr.success else "#F44336",
                ))
                # Feed result back to agent for follow-up
                ag.state.force("idle")
                follow_up = f"Command result: {result_text[:200]}\nWhat next? Reply short."
                fu_text = ""

                async def fu_delta(t: str) -> None:
                    nonlocal fu_text
                    fu_text += t

                with console.status("[#4FC3F7]Agent continues...[/]", spinner="dots"):
                    await ag.run(follow_up, StreamCallbacks(on_delta=fu_delta))
                if fu_text:
                    _render_response(fu_text)
        elif answer in ("e", "edit"):
            try:
                new_cmd = await session_pt.prompt_async(
                    HTML("<dim>$ </dim>"), style=PT_STYLE,
                )
                if new_cmd.strip():
                    tr = await tool_execute(
                        "terminal", {"command": new_cmd.strip()},
                        ToolContext(metadata={"approved": True}),
                    )
                    console.print(Panel(
                        tr.output[:500] if tr.success else f"[red]{tr.error}[/]",
                        border_style="#4CAF50" if tr.success else "#F44336",
                    ))
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            console.print("[dim][Rejected][/]")

        console.print(Rule(style="#0288D1"))


    def _render_response(text: str) -> None:
        """Render text — code blocks as panels, rest as markdown."""
        lines = text.strip().split("\n")
        in_code = False
        lang = ""
        buf: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```") and not in_code:
                # End current text buffer
                if buf:
                    console.print(Markdown("\n".join(buf)))
                    buf = []
                in_code = True
                lang = stripped[3:].strip() or "code"
                continue
            if stripped.startswith("```") and in_code:
                in_code = False
                code_content = "\n".join(buf)
                buf = []
                if lang in ("bash", "sh", "shell"):
                    console.print(Panel(code_content, title="  bash", border_style="#7C3AED", padding=(1, 2)))
                else:
                    console.print(Panel(code_content, title=f"  {lang}", border_style="#4FC3F7", padding=(1, 2)))
                continue
            buf.append(line)

        if buf:
            console.print(Markdown("\n".join(buf)))


    async def _run() -> None:
        nonlocal agent
        while True:
            try:
                user = await session_pt.prompt_async(
                    build_prompt(),
                    style=PT_STYLE,
                )
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim #4FC3F7]Ataraxic.[/]")
                break

            user = user.strip()
            if not user:
                continue
            if user in ("/quit", "/exit", "/q"):
                console.print("[dim #4FC3F7]Ataraxic.[/]")
                break
            if user in ("/clear", "/reset"):
                agent = Agent(provider=provider, max_turns=1)
                agent.system_prompt = BASE_PROMPT
                console.print("[dim][Cleared][/]")
                console.print(Rule(style="#0288D1"))
                continue
            if user == "/help":
                console.print(Panel(HELP_TEXT, title="Commands", border_style="#4FC3F7"))
                continue
            if user == "/code":
                import atar_tools.tools.file  # noqa: F401
                import atar_tools.tools.git  # noqa: F401
                import atar_tools.tools.test_runner  # noqa: F401
                agent = Agent(provider=provider, max_turns=3, tools=[1])
                agent.system_prompt = CODE_PROMPT
                cwd = os.getcwd()
                console.print(Panel(
                    f"[bold]Code mode active[/]\nWorking dir: {cwd}\n"
                    "Tools: terminal, read_file, write_file, git, run_tests\n"
                    "/chat to exit code mode",
                    border_style="#4CAF50",
                ))
                console.print(Rule(style="#0288D1"))
                continue
            if user == "/chat":
                agent = Agent(provider=provider, max_turns=1)
                agent.system_prompt = BASE_PROMPT
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#0288D1"))
                continue

            # Multi-turn: agent may need multiple rounds
            await _agent_turn(user, agent, provider)

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
