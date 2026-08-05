#!/usr/bin/env python3
"""ATAR CLI entry point."""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=False, rich_markup_mode="rich")

console = Console()


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    run: Annotated[str | None, typer.Option("--run", help="Run a single prompt and exit")] = None,
    yolo: Annotated[bool, typer.Option("--yolo", help="Auto-approve all tool calls")] = False,
) -> None:
    """ATAR — Autonomous Terminal AI Agent. Clarity in Complexity."""
    if ctx.invoked_subcommand is not None:
        return
    if run:
        from atar_core.agent import Agent, StreamCallbacks
        from atar_core.provider_registry import get_provider
        p = get_provider()
        a = Agent(provider=p, max_turns=5)
        async def d(t: str) -> None:
            typer.echo(t, nl=False)
        async def _c():
            await a.run(run, StreamCallbacks(on_delta=d))
            typer.echo()
        asyncio.run(_c())
        return
    from atar_cli.rich_repl import run_repl
    if yolo:
        from atar_core.approval import get_approval
        get_approval().yolo = True
    run_repl()


@app.command()
def tui() -> None:
    """Launch Textual TUI — full-screen interface with 25 screens."""
    from atar_tui.app import ATARApp
    app_instance = ATARApp()
    app_instance.run()


@app.command()
def ink() -> None:
    """Launch Ink/React TUI — one-command setup with real AI."""
    import os
    p = os.path.abspath(__file__)
    for _ in range(5):
        p = os.path.dirname(p)
    ink_dir = os.path.join(p, "apps", "atar-ink")
    from atar_cli.ink_launcher import launch
    launch(ink_dir)


@app.command()
def serve(port: int = 8420) -> None:
    """Start ATAR API server for frontend connections."""
    from atar_cli.api_server import start_server
    console.print(f"[green]ATAR API server → http://127.0.0.1:{port}[/]")
    start_server(port=port)


@app.command()
def web(port: int = 8420) -> None:
    """Launch ATAR Web UI — browser-based chat interface."""
    import webbrowser

    from atar_cli.api_server import start_server
    console.print(f"[bold green]ATAR Web UI → http://127.0.0.1:{port}[/]")
    console.print("[dim]Opening browser...[/]")
    webbrowser.open(f"http://127.0.0.1:{port}")
    start_server(port=port)


@app.command()
def sessions() -> None:
    """List saved sessions."""
    from atar_storage.sqlite_store import SqliteStore
    store = SqliteStore()
    for s in store.list_sessions()[:20]:
        console.print(f"  {s['session_id'][:12]} — {s.get('created_at', '?')}")


@app.command()
def remember(key: Annotated[str, typer.Option(help="Memory key")],
             value: Annotated[str, typer.Option(help="Memory value")]) -> None:
    """Save a fact to persistent memory."""
    from atar_core.memory import create_entry
    create_entry("user", f"{key}: {value}")
    console.print(f"  [green]Remembered: {key}[/]")


@app.command()
def forget(key: Annotated[str, typer.Option(help="Memory key to forget")]) -> None:
    """Forget a memory entry."""
    from atar_core.memory import forget_entry
    forget_entry(key)
    console.print(f"  [dim]Forgot: {key}[/]")


@app.command()
def doctor() -> None:
    """Diagnose environment and configuration."""
    import platform as pl
    import sys
    console.print("[bold]ATAR Doctor[/]")
    console.print(f"  Python: {pl.python_version()} ({sys.executable})")
    console.print(f"  Platform: {pl.system()} {pl.release()}")
    # Check API key
    from atar_core.provider_registry import get_provider
    try:
        provider = get_provider()
        console.print(f"  Provider: {provider.model or 'unknown'}")
        api_key = getattr(provider, 'api_key', None)
        if api_key:
            masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
            console.print(f"  API Key: {masked}")
        else:
            console.print("  API Key: [red]not set[/]")
    except Exception as e:
        console.print(f"  API Key: [red]error: {e}[/]")


@app.command()
def setup() -> None:
    """First-run setup wizard — configure AI provider."""
    import asyncio

    from atar_cli.setup_wizard import run_setup
    asyncio.run(run_setup())


@app.command()
def gateway(platform: str = "telegram") -> None:
    """Start a messaging gateway."""
    if platform == "telegram":
        import asyncio

        from atar_cli.telegram_gateway import start_telegram_gateway
        asyncio.run(start_telegram_gateway())
    else:
        console.print(f"[red]Unknown gateway: {platform}. Supported: telegram[/]")


if __name__ == "__main__":
    app()
