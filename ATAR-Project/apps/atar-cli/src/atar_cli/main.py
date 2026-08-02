"""ATAR CLI — chat + plan + code + sessions."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import typer
from atar_core.agent import Agent, StreamCallbacks
from atar_core.planning import PlanningEngine
from atar_core.session import SessionManager
from atar_security.secrets import SecretsManager

app = typer.Typer(name="atar", help="ATAR — Clarity in Complexity.")
sessions = SessionManager()


def get_provider():
    from atar_core.fake_provider import FakeModelProvider
    from atar_provider_anthropic.client import AnthropicProvider
    s = SecretsManager()
    k = s.resolve("deepseek", env_var="DEEPSEEK_API_KEY")
    if k:
        return AnthropicProvider(api_key=k, base_url="https://api.deepseek.com/anthropic", model="deepseek-v4-pro")
    return FakeModelProvider(responses=["Set DEEPSEEK_API_KEY."])


async def _run_chat(prompt: str, sid: str | None = None) -> None:
    p = get_provider()
    sess = sessions.load(sid) if sid else sessions.new()
    agent = Agent(provider=p, session_id=sess.session_id)
    for m in sess.messages:
        agent._messages.append(m)

    async def d(t: str) -> None:
        typer.echo(t, nl=False)

    r = await agent.run(prompt, StreamCallbacks(on_delta=d))
    if r:
        sess.add_message("user", prompt)
        sess.add_message("assistant", r.text)
        sessions.save()
        typer.echo()


@app.command()
def chat(
    prompt: Annotated[str | None, typer.Argument(help="Prompt")] = None,
    session: Annotated[str | None, typer.Option("--session", "-s")] = None,
) -> None:
    """Chat with ATAR."""
    if prompt:
        asyncio.run(_run_chat(prompt, session))
    else:
        for s in sessions.list()[:5]:
            typer.echo(f"  {s.session_id} — {s.title} ({len(s.messages)} msgs)")
        typer.echo("Use: atar chat 'prompt'")


@app.command()
def plan(
    goal: Annotated[str, typer.Argument(help="Goal")],
    auto_approve: Annotated[bool, typer.Option("--yes", "-y")] = False,
) -> None:
    """Generate a plan."""
    p = get_provider()

    async def _p() -> None:
        agent = Agent(provider=p)
        engine = PlanningEngine(agent)
        typer.echo(f"\n  Planning: {goal}\n")
        r = await engine.plan(goal)
        if not r.tasks:
            typer.echo("  No plan.")
            return
        typer.echo(f"  Plan: {r.title or goal}\n  Tasks: {len(r.tasks)}\n")
        icons = {"HIGH": "🔴", "CRITICAL": "⛔", "MEDIUM": "🟡", "LOW": "🟢"}
        for t in r.tasks:
            typer.echo(f"  {icons.get(str(t.risk), '⚪')} {t.title}")
        high = r.high_risk_tasks()
        if high and not auto_approve:
            typer.echo(f"\n  ⚠ {len(high)} high-risk. Use --yes.")
            return
        if auto_approve or not high:
            r.approve_all()
            typer.echo(f"\n  ✅ Approved. {len(r.tasks)} tasks.")
            sess = sessions.new(title=goal[:50])
            sess.add_message("user", f"plan: {goal}")
            sessions.save()
            typer.echo(f"  Session: {sess.session_id}")

    asyncio.run(_p())


@app.command()
def code(
    prompt: Annotated[str | None, typer.Argument(help="What to do with the codebase")] = None,
) -> None:
    """Analyze and work with code."""
    if not prompt:
        typer.echo("Usage: atar code 'analyze this project'")
        return

    import atar_tools.tools.file  # noqa
    import atar_tools.tools.terminal  # noqa
    import atar_tools.tools.git  # noqa
    import atar_tools.tools.test_runner  # noqa

    async def _code() -> None:
        p = get_provider()
        agent = Agent(
            provider=p,
            system_prompt=(
                "You are ATAR, a coding assistant. You have tools: git, terminal, "
                "read_file, write_file, run_tests. When asked to analyze or modify code, "
                "explain what you would do step by step. Mention specific commands."
            ),
        )
        async def d(t: str) -> None:
            typer.echo(t, nl=False)

        await agent.run(prompt, StreamCallbacks(on_delta=d))
        typer.echo()

    asyncio.run(_code())


@app.command()
def init() -> None:
    """Initialize ATAR."""
    os.makedirs(".atar", exist_ok=True)
    typer.echo("Initialized .atar/")


if __name__ == "__main__":
    app()
