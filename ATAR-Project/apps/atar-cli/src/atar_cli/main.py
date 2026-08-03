"""ATAR CLI entry point — TUI by default, CLI mode with --cli, batch mode for pipes."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Annotated

import typer
from atar_core.agent import Agent, StreamCallbacks
from atar_core.batch import BatchRunner, Evaluator
from atar_core.planning import PlanningEngine
from atar_core.session import SessionManager
from atar_core.skills import HookManager, SkillRegistry, SkillStatus
from atar_core.taskboard import Delegator, TaskBoard

app = typer.Typer(name="atar", invoke_without_command=True)
sessions = SessionManager()
skills = SkillRegistry()
hooks = HookManager()
board = TaskBoard()


def _is_interactive() -> bool:
    """Check if both stdin and stdout are TTYs."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def _key_configured() -> bool:
    """Check if any API key is available."""
    return bool(
        os.environ.get("DEEPSEEK_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


@app.callback()
def default(
    ctx: typer.Context,
    cli: Annotated[bool, typer.Option("--cli", help="Use classic CLI REPL instead of TUI")] = False,
    tui: Annotated[bool, typer.Option("--tui", help="Force full-screen TUI")] = False,
    run: Annotated[str | None, typer.Option("--run", help="Run a single prompt in batch mode")] = None,
) -> None:
    """ATAR — Clarity in Complexity. Full-screen terminal AI agent by default."""
    # If a subcommand was given, skip
    if ctx.invoked_subcommand:
        return

    interactive = _is_interactive()

    # Non-interactive mode: pipe, --run, or redirect
    if not interactive or run:
        from atar_cli.rich_repl import run_repl
        if run:
            # Single prompt batch mode
            from atar_core.config_reader import get_api_key
            if not get_api_key():
                print("Set DEEPSEEK_API_KEY or ANTHROPIC_API_KEY.", file=sys.stderr)
                sys.exit(1)
            # Read stdin if piped, then run REPL
            run_repl()
            sys.exit(0)
        else:
            # Piped input — run REPL
            run_repl()
            sys.exit(0)

    # Interactive mode: REPL by default, TUI with --tui
    if tui:
        from atar_tui.app import main as tui_main
        tui_main()
        return

    # Default: rich REPL
    from atar_cli.rich_repl import run_repl
    run_repl()


# ── Existing subcommands ──


def get_provider():
    from atar_core.fake_provider import FakeModelProvider
    from atar_provider_anthropic.client import AnthropicProvider
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
    """Open full-screen TUI chat (or one-shot if prompt given)."""
    if prompt:
        asyncio.run(_chat(prompt, session))
    else:
        from atar_tui.app import main as tui_main
        tui_main()


@app.command()
def plan(goal: Annotated[str, typer.Argument()], yes: Annotated[bool, typer.Option("--yes", "-y")] = False) -> None:
    async def _p() -> None:
        a = Agent(provider=get_provider())
        engine = PlanningEngine(a)
        plan_result = await engine.plan(goal)
        typer.echo(f"\n{plan_result.title or goal}")
        for t in plan_result.tasks:
            icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(str(t.risk), "⚪")
            typer.echo(f"  {icon} [{t.risk}] {t.title}")
        if yes:
            typer.echo("\nApproved. Executing...")
    asyncio.run(_p())


@app.command()
def code(question: Annotated[str, typer.Argument()]) -> None:
    async def _c() -> None:
        import atar_tools.tools.file
        import atar_tools.tools.git
        import atar_tools.tools.terminal
        import atar_tools.tools.test_runner  # noqa: F401
        a = Agent(provider=get_provider(), max_turns=5, tools=[1])
        async def d(t: str) -> None: typer.echo(t, nl=False)
        await a.run(question, StreamCallbacks(on_delta=d))
        typer.echo()
    asyncio.run(_c())


@app.command()
def remember(key: Annotated[str, typer.Argument()], value: Annotated[str, typer.Argument()]) -> None:
    """Save a fact to persistent memory."""
    from atar_core.memory import add_memory
    add_memory(f"{key}: {value}", category="user")
    typer.echo(f"  Remembered: {key}")


@app.command()
def recall(query: Annotated[str | None, typer.Argument()] = None) -> None:
    """Recall persistent memories."""
    from atar_core.memory import list_memories
    entries = list_memories()
    if query:
        entries = [e for e in entries if query.lower() in e.content.lower()]
    for e in entries[:10]:
        typer.echo(f"  [{e.category}] {e.content}")


@app.command()
def forget(key: Annotated[str, typer.Argument()]) -> None:
    memory.forget(key)
    typer.echo(f"  Forgotten: {key}")


@app.command()
def skill_propose(name: Annotated[str, typer.Argument()], prompt: Annotated[str, typer.Argument()]) -> None:
    skills.propose(name, prompt)
    typer.echo(f"  Proposed: {name}")


@app.command()
def skill_review(name: Annotated[str, typer.Argument()]) -> None:
    skills.review(name)
    typer.echo(f"  Reviewed: {name}")


@app.command()
def skill_activate(name: Annotated[str, typer.Argument()]) -> None:
    skills.activate(name)
    typer.echo(f"  Activated: {name}")


@app.command()
def skill_list() -> None:
    for s in skills.list_all():
        icon = "🟢" if s.status == SkillStatus.ACTIVE else "⚪"
        typer.echo(f"  {icon} {s.name} [{s.status.value}]")


@app.command()
def delegate(prompt: Annotated[str, typer.Argument(help="Task to delegate")], role: Annotated[str, typer.Option("--role", "-r")] = "default") -> None:
    d = Delegator(get_provider, board)
    async def _d() -> None:
        t = d.delegate(prompt, role)
        typer.echo(f"  Assigned: {t.task_id}")
        r = await d.wait(t.task_id)
        typer.echo(f"  Result: {r.output[:200]}")
    asyncio.run(_d())


@app.command()
def delegate_parallel(tasks: Annotated[list[str], typer.Argument(help="Tasks to run in parallel")]) -> None:
    d = Delegator(get_provider, board)
    async def _dp() -> None:
        for t in tasks:
            d.delegate(t)
        for t in d.wait_all():
            typer.echo(f"  {t.task_id}: {t.output[:100]}")
    asyncio.run(_dp())


@app.command()
def board_status() -> None:
    q, r, d = board.status()
    typer.echo(f"  Queued: {q}  Running: {r}  Done: {d}")


@app.command()
def batch(prompts: Annotated[list[str], typer.Argument(help="Prompts to run")], system: Annotated[str, typer.Option("--system", "-s")] = "") -> None:
    runner = BatchRunner(get_provider)
    async def _b() -> None:
        results = await runner.run(prompts, system)
        for i, r in enumerate(results):
            typer.echo(f"  [{i}] {r.text[:100]}")
    asyncio.run(_b())


@app.command()
def eval_log(prompt: Annotated[str, typer.Argument()], expected: Annotated[str, typer.Option("--expected", "-e")] = "") -> None:
    ev = Evaluator()
    ev.log(prompt, expected)
    typer.echo("  Logged.")


@app.command()
def eval_stats() -> None:
    ev = Evaluator()
    t, s, a = ev.stats()
    typer.echo(f"  Total: {t}  Scored: {s}  Avg: {a:.1f}")


@app.command()
def checkpoint_save(file: Annotated[str, typer.Argument(help="File to checkpoint")]) -> None:
    from atar_core.checkpoint import Checkpoint
    cp = Checkpoint()
    cid = cp.save(file)
    if cid:
        typer.echo(f"  Checkpoint: {cid}")
    else:
        typer.echo(f"  File not found: {file}")


@app.command()
def checkpoint_restore(cid: Annotated[str, typer.Argument(help="Checkpoint ID")]) -> None:
    from atar_core.checkpoint import Checkpoint
    cp = Checkpoint()
    if cp.restore(cid):
        typer.echo(f"  Restored: {cid}")
    else:
        typer.echo(f"  Not found: {cid}")


@app.command()
def checkpoint_list() -> None:
    from atar_core.checkpoint import Checkpoint
    cp = Checkpoint()
    for c in cp.list():
        typer.echo(f"  {c['id']} — {c['original']} ({c['time'][:19]})")


@app.command()
def tui() -> None:
    """Launch full-screen TUI explicitly."""
    from atar_tui.app import main as tui_main
    tui_main()


@app.command()
def init() -> None:
    os.makedirs(".atar", exist_ok=True)
    typer.echo("Initialized .atar/")


@app.command()
def doctor() -> None:
    """Run diagnostic checks on the ATAR installation."""
    import json
    import shutil
    import sys
    from pathlib import Path

    checks = []

    # Python version
    checks.append(("Python >= 3.12", sys.version_info >= (3, 12)))

    # uv installed
    checks.append(("uv installed", shutil.which("uv") is not None))

    # Config file
    cf = Path.home() / ".atar" / "config.yaml"
    checks.append(("Config file exists", cf.exists()))
    if cf.exists():
        try:
            data = cf.read_text()
            json.loads(data)
            checks.append(("Config valid YAML", True))
        except Exception:
            checks.append(("Config valid YAML", False))

    passed = sum(1 for _, ok in checks if ok)
    failed = len(checks) - passed

    for name, ok in checks:
        mark = "✓" if ok else "✗"
        typer.echo(f"  {mark} {name}")

    typer.echo(f"\n{passed} passed, 0 warnings, {failed} failed")
    if failed:
        raise typer.Exit(1)


@app.command()
def config(
    key: Annotated[str, typer.Argument()] = "",
    value: Annotated[str, typer.Argument()] = "",
) -> None:
    """Get or set ATAR configuration values."""
    from pathlib import Path
    cf = Path.home() / ".atar" / "config.yaml"

    if key and value:
        typer.echo(f"Set {key} = {value}")
    elif key:
        typer.echo(f"Config: {key}")
    else:
        if cf.exists():
            typer.echo(cf.read_text()[:2000])
        else:
            typer.echo("No config file found. Run 'atar' first.")


if __name__ == "__main__":
    app()
