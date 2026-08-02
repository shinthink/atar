"""ATAR CLI — multi-agent delegate command."""

from __future__ import annotations

import asyncio
import os
from typing import Annotated

import typer
from atar_core.agent import Agent, StreamCallbacks
from atar_core.batch import BatchRunner, Evaluator
from atar_core.memory import MemoryEngine, SessionSearch
from atar_core.planning import PlanningEngine
from atar_core.session import SessionManager
from atar_core.skills import HookManager, SkillRegistry, SkillStatus
from atar_core.taskboard import Delegator, TaskBoard

app = typer.Typer(name="atar", invoke_without_command=True)


@app.callback()
def default() -> None:
    """Launch ATAR TUI by default (no subcommand)."""
    from atar_tui.app import main as tui_main
    tui_main()
sessions = SessionManager()
memory = MemoryEngine()
skills = SkillRegistry()
hooks = HookManager()
board = TaskBoard()


def get_provider():
    from atar_core.fake_provider import FakeModelProvider
    from atar_provider_anthropic.client import AnthropicProvider
    # Provider resolves key from env automatically
    prov = AnthropicProvider(base_url="https://api.deepseek.com/anthropic", model="deepseek-v4-pro")
    if prov.api_key:
        return prov
    return FakeModelProvider(responses=["Set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY."])


async def _chat(prompt: str, sid: str | None = None) -> None:
    p = get_provider()
    sess = sessions.load(sid) if sid else sessions.new()
    agent = Agent(provider=p, session_id=sess.session_id)
    for m in sess.messages:
        agent._messages.append(m)
    for s in skills.list_active():
        agent.system_prompt += f"\nSkill: {s.name} — {s.prompt}"

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
    prompt: Annotated[str | None, typer.Argument()] = None,
    session: Annotated[str | None, typer.Option("--session", "-s")] = None,
) -> None:
    if prompt:
        asyncio.run(_chat(prompt, session))


@app.command()
def plan(goal: Annotated[str, typer.Argument()], yes: Annotated[bool, typer.Option("--yes", "-y")] = False) -> None:
    async def _p() -> None:
        a = Agent(provider=get_provider())
        r = await PlanningEngine(a).plan(goal)
        if r.tasks:
            for t in r.tasks:
                typer.echo(f"  {'🔴' if str(t.risk)=='HIGH' else '🟢'} {t.title}")
            if yes:
                r.approve_all()
                typer.echo(f"\n  ✅ {len(r.tasks)} approved.")
    asyncio.run(_p())


@app.command()
def code(prompt: Annotated[str | None, typer.Argument()] = None) -> None:
    import atar_tools.tools.file  # noqa
    import atar_tools.tools.terminal  # noqa
    import atar_tools.tools.git  # noqa
    import atar_tools.tools.test_runner  # noqa
    import atar_tools.tools.web  # noqa
    async def _c() -> None:
        a = Agent(provider=get_provider())
        async def d(t: str) -> None: typer.echo(t, nl=False)
        await a.run(prompt, StreamCallbacks(on_delta=d))
        typer.echo()
    if prompt:
        asyncio.run(_c())


@app.command()
def search(query: Annotated[str, typer.Argument()]) -> None:
    for sess, snips in SessionSearch(sessions).search(query):
        typer.echo(f"\n  📁 {sess.title}")
        for s in snips:
            typer.echo(f"     {s}")


@app.command()
def remember(key: Annotated[str, typer.Argument()], value: Annotated[str, typer.Argument()]) -> None:
    memory.save(key, value)
    typer.echo(f"  ✅ {key}")


@app.command()
def recall(query: Annotated[str | None, typer.Argument()] = None) -> None:
    if query:
        for k, v in memory.search(query):
            typer.echo(f"  {k}: {v}")
    else:
        for k, v in memory.all().items():
            typer.echo(f"  {k}: {v}")


@app.command()
def forget(key: Annotated[str, typer.Argument()]) -> None:
    memory.forget(key)
    typer.echo(f"  ✅ {key}")


@app.command()
def skill_propose(name: Annotated[str, typer.Argument()], prompt: Annotated[str, typer.Argument()]) -> None:
    s = skills.propose(name, prompt)
    typer.echo(f"  ✅ {s.name} [{s.status.value}]")


@app.command()
def skill_review(name: Annotated[str, typer.Argument()]) -> None:
    s = skills.review(name)
    if s:
        typer.echo(f"  ✅ {s.name} [{s.status.value}]")


@app.command()
def skill_activate(name: Annotated[str, typer.Argument()]) -> None:
    s = skills.activate(name)
    if s:
        typer.echo(f"  ✅ {s.name}")


@app.command()
def skill_list() -> None:
    for s in skills.list_all():
        typer.echo(f"  {'🟢' if s.status == SkillStatus.ACTIVE else '⚪'} {s.name} [{s.status.value}]")


# ── Multi-Agent ──

@app.command()
def delegate(
    prompt: Annotated[str, typer.Argument(help="Task to delegate")],
    role: Annotated[str, typer.Option("--role", "-r")] = "default",
) -> None:
    """Delegate a task to a subagent."""
    d = Delegator(get_provider, board)

    async def _d() -> None:
        typer.echo(f"  🚀 Delegating [{role}]: {prompt[:60]}...")
        result = await d.delegate(prompt, role)
        typer.echo(f"\n  {result[:500]}")
        s = board.status()
        typer.echo(f"\n  Board: {s['done']} done, {s['running']} running, {s['queued']} queued")

    asyncio.run(_d())


@app.command()
def delegate_parallel(tasks: Annotated[list[str], typer.Argument(help="Tasks to run in parallel")]) -> None:
    """Delegate multiple tasks in parallel."""
    d = Delegator(get_provider, board)
    parsed = [(t, "default") for t in tasks]

    async def _dp() -> None:
        typer.echo(f"  🚀 Running {len(parsed)} tasks in parallel...")
        results = await d.delegate_parallel(parsed)
        for prompt, result in results:
            typer.echo(f"\n  ✅ {prompt[:40]} → {result[:200]}")

    asyncio.run(_dp())


@app.command()
def board_status() -> None:
    """Show task board status."""
    s = board.status()
    typer.echo(f"  Queued: {s['queued']} | Running: {s['running']} | Done: {s['done']}")
    for t in board.active():
        typer.echo(f"  [{t.status.value}] {t.id}: {t.prompt[:60]}")


@app.command()
def batch(
    prompts: Annotated[list[str], typer.Argument(help="Prompts to run")],
    system: Annotated[str, typer.Option("--system", "-s")] = "",
) -> None:
    """Run multiple prompts in batch."""
    runner = BatchRunner(get_provider)

    async def _b() -> None:
        results = await runner.run_batch(prompts, system)
        for r in results:
            status = "❌" if r["error"] else "✅"
            typer.echo(f"  {status} {r['prompt'][:50]} → {r['response'][:100]}")

    asyncio.run(_b())


@app.command()
def eval_log(
    prompt: Annotated[str, typer.Argument()],
    expected: Annotated[str, typer.Option("--expected", "-e")] = "",
) -> None:
    """Log an evaluation run."""
    evaluator = Evaluator()

    async def _e() -> None:
        provider = get_provider()
        agent = Agent(provider=provider, system_prompt="Be concise.", max_turns=2)
        response = await agent.run(prompt, StreamCallbacks())
        evaluator.log(prompt, response.text if response else "", expected)
        typer.echo(f"  ✅ Logged: {prompt[:50]}")

    asyncio.run(_e())


@app.command()
def eval_stats() -> None:
    """Show evaluation statistics."""
    s = Evaluator().stats()
    typer.echo(f"  Total: {s['total']} | Scored: {s['scored']} | Avg: {s['avg_score']}")


@app.command()
def checkpoint_save(
    file: Annotated[str, typer.Argument(help="File to checkpoint")],
) -> None:
    """Save a checkpoint of a file."""
    from atar_core.checkpoint import Checkpoint
    cp = Checkpoint()
    cid = cp.save(file)
    if cid:
        typer.echo(f"  ✅ Checkpoint: {cid}")
    else:
        typer.echo(f"  ❌ File not found: {file}")


@app.command()
def checkpoint_restore(
    cid: Annotated[str, typer.Argument(help="Checkpoint ID")],
) -> None:
    """Restore a file from checkpoint."""
    from atar_core.checkpoint import Checkpoint
    cp = Checkpoint()
    if cp.restore(cid):
        typer.echo(f"  ✅ Restored: {cid}")
    else:
        typer.echo(f"  ❌ Checkpoint not found: {cid}")


@app.command()
def checkpoint_list() -> None:
    """List all checkpoints."""
    from atar_core.checkpoint import Checkpoint
    cp = Checkpoint()
    for c in cp.list():
        typer.echo(f"  {c['id']} — {c['original']} ({c['time'][:19]})")


@app.command()
def tui() -> None:
    """Launch full-screen TUI."""
    from atar_tui.app import main
    main()


@app.command()
def init() -> None:
    os.makedirs(".atar", exist_ok=True)
    typer.echo("Initialized .atar/")


if __name__ == "__main__":
    app()
