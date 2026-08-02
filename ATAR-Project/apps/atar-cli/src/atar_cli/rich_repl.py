"""ATAR CLI — Hermes-style Rich REPL with autocomplete, tools, sessions."""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

console = Console()
session_pt = PromptSession(
    completer=WordCompleter(
        ["/help","/model","/sessions","/code","/chat","/clear","/quit","/exit","/q","/status","/tools","/reset"],
        sentence=True,
        meta_dict={"/help":"Commands","/model":"Switch model","/sessions":"Sessions","/code":"Code mode","/chat":"Chat mode","/clear":"Reset","/quit":"Exit","/exit":"Exit","/q":"Quit","/status":"Status","/tools":"Tools","/reset":"Reset"},
    ),
)

PT_STYLE = Style.from_dict({"prompt":"#4FC3F7 bold","separator":"#0288D1"})

MODELS = [
    ("DeepSeek V3","deepseek","deepseek-chat","https://api.deepseek.com/v1"),
    ("DeepSeek V4","deepseek","deepseek-v4-pro","https://api.deepseek.com/anthropic"),
    ("OpenAI","openai","gpt-4o","https://api.openai.com/v1"),
    ("Anthropic","anthropic","claude-sonnet-4-20250514","https://api.anthropic.com"),
    ("OpenRouter","openrouter","deepseek/deepseek-chat","https://openrouter.ai/api/v1"),
]

BASE_PROMPT = (
    "You are ATAR, a precise AI assistant. Respond naturally to questions. "
    "Only propose bash commands when the user explicitly asks you to create files, "
    "run programs, or make system changes. When you do, wrap the command in ```bash. "
    "For normal conversation, just answer directly. Be helpful and concise."
)


def show_banner(model: str, cwd: str, session_id: str) -> None:
    """Hermes-style two-column banner."""
    info = Table.grid(padding=(0,1))
    info.add_column(style="bold #4FC3F7",justify="left")
    info.add_column(style="dim",justify="left")
    info.add_row(model,"DeepSeek")
    info.add_row("","")
    info.add_row("Session:",session_id)
    info.add_row("CWD:",cwd)
    info.add_row("","")
    info.add_row("Tools:","read_file write_file terminal web_fetch git run_tests")
    info.add_row("","/help for commands")

    layout = Table.grid(padding=(0,2))
    layout.add_column(justify="left",width=50)
    layout.add_column(justify="left")

    logo_lines = [
        " █████╗ ████████╗ █████╗ ██████╗",
        "██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗",
        "███████║   ██║   ███████║██████╔╝",
        "██╔══██║   ██║   ██╔══██║██╔══██╗",
        "██║  ██║   ██║   ██║  ██║██║  ██║",
        "╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
    ]
    colors = ["#4FC3F7","#29B6F6","#0288D1","#0277BD","#01579B","#01579B"]
    left = Text()
    for i, line in enumerate(logo_lines):
        left.append(Text(line+"\n",style=f"bold {colors[i]}"))
    left.append(Text("\nCLARITY IN COMPLEXITY",style="bold #4FC3F7"))
    layout.add_row(left,Panel(info,border_style="#0288D1",padding=(1,2)))
    console.print(Panel(layout,border_style="#0288D1",padding=(1,2)))
    console.print(Text("  /quit · /clear · /code · /chat · /help",style="dim #4FC3F7"))
    console.print(Rule(style="#0288D1"))


def run_repl() -> None:
    from atar_core.agent import Agent, StreamCallbacks
    from atar_models.tools import ToolContext
    from atar_provider_deepseek.client import DeepSeekProvider
    from atar_tools.registry import execute as tool_execute

    key = os.environ.get("DEEPSEEK_API_KEY") or ""
    if not key:
        console.print("[red]Set DEEPSEEK_API_KEY.[/]")
        return

    provider = DeepSeekProvider(api_key=key, model="deepseek-chat")
    agent = Agent(provider=provider, max_turns=1)
    agent.system_prompt = BASE_PROMPT
    session_id = uuid.uuid4().hex[:12]
    show_banner("deepseek-chat", os.getcwd(), session_id)

    async def _agent_turn(prompt: str, ag: Agent) -> None:
        ag.state.force("idle")
        response_text = ""
        start_time = time.time()

        async def delta(t: str) -> None:
            nonlocal response_text
            response_text += t

        with console.status("[#4FC3F7]Thinking...[/]", spinner="dots"):
            await ag.run(prompt, StreamCallbacks(on_delta=delta))

        elapsed = time.time() - start_time
        console.print(Rule(style="#0288D1"))

        if not response_text:
            console.print(Rule(style="#0288D1"))
            return

        # Render with Obsidian panels
        lines = response_text.strip().split("\n")
        in_code, lang, buf = False, "", []
        for line in lines:
            s = line.strip()
            if s.startswith("```") and not in_code:
                if buf: console.print(Markdown("\n".join(buf))); buf = []
                in_code = True; lang = s[3:].strip() or "code"
                continue
            if s.startswith("```") and in_code:
                in_code = False
                code = "\n".join(buf); buf = []
                console.print(Panel(code, title=f"  {lang}", border_style="#7C3AED" if lang in ("bash","sh","shell") else "#4FC3F7", padding=(1,2)))
                continue
            buf.append(line)
        if buf: console.print(Markdown("\n".join(buf)))

        # Extract bash commands for approval
        cmds = re.findall(r"```(?:bash|shell|sh)\n(.*?)```", response_text, re.DOTALL)
        cmds = [c.strip() for c in cmds if c.strip()]
        if cmds:
            console.print(Panel("\n".join(f"[dim]$[/] [bold #4FC3F7]{c[:150]}[/]" for c in cmds), title="Proposed Commands", border_style="#FFD700"))
            try:
                answer = await session_pt.prompt_async(HTML("<yellow>Run? (y/n)</yellow> <dim>[n]</dim> "), style=PT_STYLE)
            except (EOFError, KeyboardInterrupt):
                answer = "n"
            if answer.strip().lower() in ("y","yes"):
                for c in cmds:
                    tr = await tool_execute("terminal",{"command":c},ToolContext(metadata={"approved":True}))
                    console.print(Panel(tr.output[:500] if tr.success else f"[red]{tr.error}[/]", title=f"$ {c[:80]}", border_style="#4CAF50" if tr.success else "#F44336"))
            else:
                console.print("[dim][Rejected][/]")
        console.print(Rule(style="#0288D1"))

    async def _run() -> None:
        nonlocal agent
        while True:
            try:
                user = await session_pt.prompt_async(HTML("<prompt>· </prompt>"), style=PT_STYLE)
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Ataraxic.[/]")
                break
            user = user.strip()
            if not user: continue
            if user in ("/quit","/exit","/q"):
                console.print("[dim]Ataraxic.[/]"); break
            if user in ("/clear","/reset"):
                agent = Agent(provider=provider, max_turns=1)
                agent.system_prompt = BASE_PROMPT
                console.print("[dim][Cleared][/]")
                console.print(Rule(style="#0288D1")); continue
            if user == "/help":
                console.print(Panel("/code  coding mode · /chat  chat mode\n/model  switch AI model\n/sessions  manage sessions\n/clear  reset · /quit  exit", title="Commands", border_style="#4FC3F7"))
                continue
            if user == "/model":
                # Inline model picker — async, updates agent
                lines_m = []
                for i,(name,_prov,model,_url) in enumerate(MODELS):
                    m="▸" if i==0 else " "; lines_m.append(f" {m} [{i}] {name} — {model}")
                console.print(Panel("\n".join(lines_m),title="📡 Switch Model",border_style="#FFD700"))
                try:
                    c=await session_pt.prompt_async("Pick model number: ",style=PT_STYLE)
                    idx=int(c)
                    if 0<=idx<len(MODELS):
                        name,prov_id,model,url=MODELS[idx]
                        ag=Agent(provider=provider,max_turns=1)
                        ag.system_prompt=BASE_PROMPT
                        agent=ag
                        console.print(f"[green]✓ Switched to {name} — {model}[/]")
                except (ValueError,EOFError,KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#0288D1")); continue
            if user == "/sessions":
                from atar_core.session import SessionManager
                mgr=SessionManager(); sessions=mgr.list()
                if not sessions: console.print("[dim]No sessions.[/]")
                else:
                    lines_s=[f" [{i}] {s.title or s.session_id[:12]}" for i,s in enumerate(sessions)]
                    console.print(Panel("\n".join(lines_s),title="📂 Sessions",border_style="#FFD700"))
                    try:
                        cs=await session_pt.prompt_async("Pick session: ",style=PT_STYLE)
                        idx=int(cs)
                        if 0<=idx<len(sessions):
                            s=sessions[idx]
                            ag=Agent(provider=provider,max_turns=1)
                            ag.system_prompt=BASE_PROMPT
                            for m in getattr(s,"messages",[])[-20:]: ag._messages.append(m)
                            agent=ag
                            console.print(f"[green]✓ Session: {s.title or s.session_id[:12]}[/]")
                    except (ValueError,EOFError,KeyboardInterrupt):
                        console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#0288D1")); continue
            if user == "/code":
                agent = Agent(provider=provider, max_turns=3, tools=[1])
                agent.system_prompt = "CODE mode. Use terminal, read_file, write_file, git, run_tests."
                console.print(Panel("[bold]Code mode[/] · /chat to exit",border_style="#4CAF50"))
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
