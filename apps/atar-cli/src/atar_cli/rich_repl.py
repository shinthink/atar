"""ATAR Classic REPL — streaming, tools, sessions."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
import uuid
from contextlib import suppress

from prompt_toolkit import PromptSession
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

# ── Terminal capabilities (resolved at render time) ──
_HAS_COLOR = os.environ.get("NO_COLOR") is None and os.environ.get("TERM") != "dumb"
# Width is now dynamic — call get_term_width() instead of get_term_width()
console = Console(color_system="auto" if _HAS_COLOR else None)  # no fixed width


def get_term_width() -> int:
    """Current terminal width — call at render time, not import."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80


# PromptSession created lazily — not at import
_session_pt = None


def _get_session() -> PromptSession:
    global _session_pt
    if _session_pt is None:
        _session_pt = PromptSession(
            completer=SlashCommandToolCompleter(),
            key_bindings=bindings,
            multiline=True,  # Real multiline
            history=FileHistory(os.path.expanduser("~/.atar/history.txt")),
        )
    return _session_pt

# ── Slash commands (from registry) ──
from atar_core.commands import register_command  # noqa: E402
from atar_core.commands import registry as cmd_registry  # noqa: E402

# Register all commands
register_command("/help", "Show available commands", aliases=["/h"], category="system")
from atar_core.interaction import (  # noqa: E402
    get_busy_mode,
    get_pending_bg_results,
    mark_busy_hint_shown,
    should_show_busy_hint,
)
from atar_core.prompt import assemble as assemble_prompt  # noqa: E402
from atar_core.provider_registry import PROVIDERS as _PROVIDERS  # noqa: E402
from atar_core.provider_registry import get_provider  # noqa: E402
from atar_models.requests import Message  # noqa: E402

PROVIDER_MODELS = {pid: prof.default_models for pid, prof in _PROVIDERS.items()}
MODELS = [(prof.display_name, pid, prof.default_model) for pid, prof in _PROVIDERS.items()]
register_command("/model", "Switch AI model", category="model", arg_hint="[name]")
register_command("/sessions", "Manage sessions", aliases=["/s"], category="session")
register_command("/checkpoints", "List file checkpoints", category="session")
register_command("/restore", "Restore from checkpoint", category="session", arg_hint="[id]")
register_command("/code", "Coding mode", category="tools")
register_command("/chat", "Chat mode", category="tools")
register_command("/clear", "Reset conversation", aliases=["/reset"], category="session")
register_command("/quit", "Exit ATAR", aliases=["/exit", "/q"], category="system")
register_command("/status", "Show runtime status", category="system")
register_command("/memory", "Show persistent memories", category="memory")
register_command("/remember", "Save a fact to memory", category="memory", arg_hint="[text]")
register_command("/memory forget", "Forget a memory entry", category="memory", arg_hint="[id]")
register_command("/search", "Search past sessions", category="session", arg_hint="[query]")
register_command("/checkpoints", "List file checkpoints in session", category="system")
register_command("/undo", "Undo the last turn", category="session")
register_command("/retry", "Retry the last turn", category="session")
register_command("/compress", "Compress conversation context", category="session")
register_command("/toolset", "Switch active toolset", aliases=["/ts"], category="tools", arg_hint="[name]")
register_command("/personality", "Switch or list personas", aliases=["/p"], category="model", arg_hint="[name]")
register_command("/usage", "Show current session usage", category="system")
register_command("/insights", "Show cross-session insights", category="system", arg_hint="[--days N]")


# ── Keybindings ──
bindings = KeyBindings()


@bindings.add("enter")
def _(event):
    """Enter submits in multiline mode."""
    buf = event.current_buffer
    if buf.text.strip():
        buf.validate_and_handle()


@bindings.add("escape", "enter")
def _(event):
    """Alt+Enter inserts newline."""
    event.current_buffer.insert_text("\n")


@bindings.add("c-j")
def _(event):
    """Ctrl+J inserts newline."""
    event.current_buffer.insert_text("\n")


class SlashCommandToolCompleter(Completer):
    """Completer that shows all slash commands + tools when typing '/'."""

    @staticmethod
    def _tool_risk(tool_name: str) -> tuple[str, str]:
        from atar_cli.rich_repl_helpers import tool_risk
        return tool_risk(tool_name)

    def get_completions(self, document: Document, complete_event):
        text_before = document.text_before_cursor
        # Only trigger for slash commands (text starts with /)
        if not text_before.strip().startswith("/"):
            return

        word = text_before.strip()
        # If cursor is past the first word, don't complete
        if " " in text_before.strip() and not word.startswith("/"):
            return

        # Get slash commands from registry
        cmds = cmd_registry.completions()
        matching = [c for c in cmds if c.startswith(word)]

        # If user typed only "/" or "/<partial>", show matching commands
        if word == "/" or matching:
            for cmd_name in sorted(matching if matching else list(cmds)):
                cmd = cmd_registry.get(cmd_name)
                if not cmd:
                    continue
                display_meta = cmd.description
                if cmd.aliases:
                    display_meta += f" ({', '.join(cmd.aliases)})"
                yield Completion(
                    cmd_name,
                    start_position=-len(word),
                    display_meta=display_meta,
                    style="fg:#67D8FF bold",
                    selected_style="bg:#1a1a2e fg:#67D8FF bold",
                )

            # Also show tools after commands when user just typed "/"
            if word == "/" or not matching:
                from atar_tools.registry import list_all as _list_tools
                tools = _list_tools()
                seen = set()
                for t in tools:
                    if t.name in seen:
                        continue
                    seen.add(t.name)
                    risk, color = self._tool_risk(t.name)
                    yield Completion(
                        f"/{t.name}",
                        start_position=-len(word),
                        display_meta=f"[{risk}] {t.description[:60]}" if hasattr(t, 'description') else f"[{risk}]",
                        style=f"fg:{color}",
                        selected_style=f"bg:#1a1a2e fg:{color}",
                    )


@bindings.add("c-c")
def _(event):
    event.current_buffer.text = ""


@bindings.add("c-v")
def _(event):
    data = event.app.clipboard.get_data()
    text = data.text if isinstance(data, ClipboardData) else str(data)
    event.current_buffer.insert_text(text)
    # Show compact indicator without losing content
    if len(text) > 500:
        pass  # Keep full content, indicator in status bar if needed



PT_STYLE = Style.from_dict({
    "prompt": "#67D8FF bold",
    "toolbar": "bg:default #7F8C98",
    "bottom-toolbar": "bg:default #7F8C98 noreverse",
    "bottom-toolbar.text": "bg:default #7F8C98 noreverse",
})


# ── Model selection ──
from atar_core.provider_registry import PROVIDERS as _PROVIDERS  # noqa: E402

MODELS = [(prof.display_name, pid, prof.default_model) for pid, prof in _PROVIDERS.items()]


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


def _create_provider(session_id: str = ""):
    from atar_core.agent import Agent
    from atar_core.provider_router import create_router
    try:
        router = create_router()
        first = router.providers[0]
        cfg = _read_config()
        model = cfg.get("model") or getattr(first, "model", "deepseek-v4-flash")
        agent = Agent(provider=router, max_turns=8, tools=[1], interactive=True)
        prompt = assemble_prompt(session_id=session_id, model=model, cwd=os.getcwd())
        agent.system_prompt = prompt.full
        return router, model, agent
    except RuntimeError as e:
        console.print(f"[red]{e}[/]")
        return None, "none", None


def _switch_model(provider_id: str, model_id: str) -> str:
    """Switch to a specific provider+model. Returns display string."""
    prof = get_provider(provider_id)
    name = prof.display_name if prof else provider_id
    cfg = _read_config()
    cfg["provider"] = provider_id
    cfg["model"] = model_id
    _save_config(cfg)
    return f"{name} — {model_id}"

def show_banner(model: str, cwd: str, session_id: str) -> None:
    """Compact responsive banner — 3-4 lines at any width."""
    from atar_core.theme import current_theme
    theme = current_theme()
    c = theme.colors
    w = get_term_width()
    short_cwd = cwd.replace(os.path.expanduser("~"), "~")
    if len(short_cwd) > 50:
        parts = short_cwd.split("/")
        short_cwd = ".../" + "/".join(parts[-2:]) if len(parts) > 2 else short_cwd

    # Count tools from registry (real, not hardcoded)
    from atar_tools.registry import list_all as _list_tools
    from atar_tools.toolsets import enabled_toolsets
    all_tools = _list_tools()
    tool_count = len(all_tools)
    tset_count = len(enabled_toolsets())

    if w < 60:
        console.print(f"[bold {c.primary}]ATAR[/] [dim]— {model} · {short_cwd}[/]")
    elif w < 80:
        console.print(f"[bold {c.primary}]ATAR[/] — Clarity in Complexity.")
        console.print(f"[dim]{model} · {short_cwd} · {tool_count} tools · /help[/]")
    else:
        console.print(f"[bold {c.primary}]ATAR[/] — Clarity in Complexity.")
        console.print(f"[dim]{model} · {short_cwd} · session {session_id[:8]}[/]")
        console.print(f"[dim]{tool_count} tools · {tset_count} toolsets · /help[/]")
    console.print("")


_last_diff: list[str] = []
_pending_queue: list[str] = []
_last_rejection_feedback: dict[str, str] = {}

# ── Runtime stats for status bar ──
_stats = {"turns": 0, "tools": 0, "tokens": 0, "tokens_out": 0, "start_time": None, "model": "deepseek-chat", "compressions": 0, "background_tasks": 0, "cost": 0.0}




def _context_bar() -> str:
    from atar_cli.rich_repl_helpers import compute_context_bar
    tokens = _stats.get("tokens") or 0
    if tokens == 0:
        est = _stats.get("text_chars") or 0
        tokens = max(tokens, est // 3)
        tokens = max(tokens, _stats["turns"] * 200)
    return compute_context_bar(tokens, 128000)


def _status_bar() -> str:
    import time as _t

    if _stats["start_time"] is None:
        _stats["start_time"] = _t.time()
    e = int(_t.time() - _stats["start_time"])
    m, s = divmod(e, 60)
    d = f"{m}m{s:02d}s" if m > 0 else f"{s}s"
    from atar_core.display import context_bar
    ctx, _ = context_bar(_stats["tokens"] + _stats["tokens_out"], 128000)
    c = f"${_stats['cost']:.2f}" if _stats["cost"] > 0 else "$0"
    thinking = " ● thinking..." if _stats.get("_thinking") else ""
    return f"◆ {_stats['model']} │ {ctx} │ turns {_stats['turns']} │ tools {_stats['tools']} │ {c} │ {d}{thinking}"

def _try_resume_session() -> object | None:
    """Try to resume the last session from storage."""
    try:
        from atar_core.session import SessionManager
        mgr = SessionManager()
        sessions = mgr.list()
        if sessions:
            return sessions[-1]  # most recent
    except Exception:
        pass
    return None


def run_repl() -> None:
    import atar_tools.tools.file
    import atar_tools.tools.terminal
    import atar_tools.tools.web
    import atar_tools.tools.web_search  # noqa: F401
    from atar_core.agent import Agent, StreamCallbacks

    session_id = uuid.uuid4().hex[:12]

    provider, model, agent = _create_provider(session_id)
    if not provider or not agent:
        console.print("[red]Set DEEPSEEK_API_KEY.[/]")
        return

    # Fresh session — no auto-resume to avoid old context contamination
    show_banner(model, os.getcwd(), session_id)
    import time as _t
    _stats["model"] = model
    _stats["start_time"] = _t.time()

    _current_task: asyncio.Task | None = None
    _interrupt = False
    async def _agent_turn(prompt: str, ag: Agent) -> None:
        _stats["turns"] += 1
        import time as _t2
        _t_start = _t2.time()
        response_text = ""
        _had_tools = False
        _tool_start_time: dict[str, float] = {}
        _last_tool_id: set[str] = set()
        _tool_results: list[str] = []
        args_cache: dict[str, dict] = {}

        async def on_tool(name: str, args: dict) -> None:
            nonlocal response_text, _had_tools
            _had_tools = True
            response_text = ""
            tool_sig = f"{name}:{args.get('path', '')}" if name in ("write_file", "read_file") else f"{name}:{str(args)}"
            if tool_sig in _last_tool_id:
                return
            _last_tool_id.add(tool_sig)
            args_cache[name] = args
            _stats["tools"] += 1
            _tool_start_time[name] = _t2.time()
            from atar_core.display_v2 import tool_color as _tc
            from atar_core.display_v2 import tool_icon as _ti
            from atar_core.display_v2 import tool_label as _tl
            icon = _ti(name)
            label = _tl(name)
            color = _tc(name)
            short = str(args)[:60]
            if name in ("read_file", "write_file"):
                short = args_cache[name].get("path", str(args))[:60]
            elif name == "terminal":
                short = f"$ {args.get('command', '')[:60]}"
            console.print(f"\n  [{color}]{icon}[/] [bold {color}]{label}[/] [dim]{short}[/]")

        async def on_tool_result(name: str, result: str) -> None:
            """Collect results for display after Status exits."""
            a = args_cache.get(name, {})
            if name == "terminal":
                preview = a.get("command", "")[:50]
                if result:
                    preview_text = (result or "").strip()[:80].replace("\n", " ")
                    _tool_results.append(f"  [dim]└─ {preview_text}{'...' if len(result or '') > 80 else ''}[/]")
                else:
                    preview = a.get("command", "")[:50] or a.get("path", "")[:50] or a.get("query", "")[:50]
                    _tool_results.append(f"  [dim]└─ {preview}[/]")
                return

        try:
            async def on_approval(tool_name: str, arguments: dict) -> bool:
                # Auto-approve safe/read-only terminal commands
                if tool_name == "terminal":
                    cmd = arguments.get("command", "")
                    if cmd:
                        from atar_tools.tools.terminal import _is_readonly_command
                        if _is_readonly_command(cmd):
                            return True

                from atar_core.approval import get_approval
                approval = get_approval()
                file_path = arguments.get("path", "") or arguments.get("file_path", "")
                action = approval.resolve(tool_name, file_path)
                if action == "approve":
                    return True
                if action == "reject":
                    console.print(f"[red]✗ {tool_name} auto-rejected (permission: never)[/]")
                    return False
                # action == "ask" — simple inline prompt
                from atar_core.display_v2 import tool_color as _tc2
                from atar_core.display_v2 import tool_icon as _ti2
                from atar_core.display_v2 import tool_label as _tl2
                from rich.prompt import Prompt
                console.print(f"  [{_tc2(tool_name)}]{_ti2(tool_name)}[/] [bold]{_tl2(tool_name)}[/] [dim]({file_path or str(arguments)[:60]})[/]")
                try:
                    choice = Prompt.ask("  Run?", choices=["y", "n", "a"], default="y", show_choices=False)
                except (KeyboardInterrupt, EOFError):
                    return False
                choice = choice.strip().lower()
                if choice in ("y", "yes", "1"):
                    return True
                if choice == "a":
                    approval.set_tool_mode(tool_name, "always")
                    return True
                if choice == "n" or choice in ("no", "2", "3", "4", "5"):
                    return False
                # Default: reject
                return False

            async def _capture(t: str) -> None:
                nonlocal response_text
                response_text += t
                _stats["tokens_out"] += 1
                # Stream text in real-time (not just buffer)
                if len(response_text) == 1:
                    console.print()
                    from atar_core.theme import current_theme
                    c = current_theme().colors
                    console.print(f"[bold {c.primary}]  ATAR[/]")
                # Print deltas directly for real-time streaming
                console.print(t, end="")

            # ── Ctrl+C handler during agent run ──
            _cancel_requested = False

            def _on_sigint(signum, frame):
                nonlocal _cancel_requested
                _cancel_requested = True

            import signal
            old_handler = signal.signal(signal.SIGINT, _on_sigint)
            from atar_core.display_v2 import calculate_cost

            async def _run_agent():
                # Show "thinking" in status bar
                _stats["_thinking"] = True
                try:
                    # Run agent with cancellation support
                    agent_task = asyncio.create_task(ag.run(prompt, StreamCallbacks(
                        on_delta=_capture, on_tool_call=on_tool, on_tool_result=on_tool_result,
                        on_approval=on_approval,
                        get_rejection_feedback=lambda: _last_rejection_feedback.get("text"),
                    )))
                    # Poll for cancellation
                    while not agent_task.done():
                        if _cancel_requested:
                            agent_task.cancel()
                            console.print("\n[dim]⏸ Cancelled.[/]")
                            break
                        await asyncio.sleep(0.1)
                    if not _cancel_requested:
                        await agent_task
                finally:
                    _stats["_thinking"] = False
                    # Restore signal handler
                    signal.signal(signal.SIGINT, old_handler)
                    # End streaming line
                    if response_text:
                        console.print("\n")
            await _run_agent()
            for tr in _tool_results:
                console.print(tr)
            _stats["cost"] += calculate_cost(_stats["model"], _stats["tokens"], _stats["tokens_out"])
        except asyncio.CancelledError:
            console.print("\n[dim]\u23f9 Interrupted[/]")
            return
        _stats["last_response"] = _t2.time() - _t_start

        if not response_text.strip():
            if _had_tools:
                response_text = "_Work completed — see tool results above._"
            else:
                console.print(Rule(style="#394B59"))
                return

        # Response — light rail style, no heavy panel
        console.print()
        from atar_core.theme import current_theme
        c = current_theme().colors
        # Left rail prefix
        console.print(f"[bold {c.primary}]  ATAR[/]")
        for line in response_text.split("\n"):
            console.print(f"  [dim]│[/] {line}")
        console.print()



        # Process pending queue
        if _pending_queue:
            nxt = _pending_queue.pop(0)
            _current_task = asyncio.create_task(_agent_turn(nxt, agent))
            console.print(f"[dim]Running queued: {nxt[:60]}[/]")
        # Display background results
        for bg in get_pending_bg_results():
            console.print(Panel(
                Markdown(bg.result or "(no output)"),
                title=f"Background #{bg.task_id}",
                border_style="#67D8FF",
                padding=(1,2)))

    async def _run() -> None:
        nonlocal provider, model, agent, _current_task, _interrupt
        while True:
            try:
                user = await _get_session().prompt_async(
                    HTML("<prompt>\u203a </prompt>"), style=PT_STYLE, bottom_toolbar=_status_bar,
                )
            except KeyboardInterrupt:
                if _current_task and not _current_task.done():
                    _current_task.cancel()
                    console.print("\n[dim]⏸ Interrupted — type your redirect (or press Ctrl+C again to cancel):[/]")
                    try:
                        redirect = await _get_session().prompt_async(
                            HTML(""), style=PT_STYLE
                        )
                        if redirect.strip():
                            # Inject redirect into agent context as continuation
                            agent._messages.append(Message(role="user", content=f"[Redirect] {redirect.strip()}"))
                            console.print(f"[dim]↳ Redirected: {redirect[:60]}...[/]")
                            _current_task = asyncio.create_task(_agent_turn("", agent))
                    except KeyboardInterrupt:
                        console.print("\n[dim]Cancelled.[/]")
                        continue
                    continue
                console.print("\n[dim]Press Ctrl+D to exit.[/]")
                continue
            except EOFError:
                try:
                    confirm = await _get_session().prompt_async(
                        HTML("\n<dim>Exit ATAR? (y/N)</dim> "), style=PT_STYLE, bottom_toolbar=_status_bar,
                    )
                    if confirm.strip().lower() in ("y", "yes"):
                        console.print("\n[dim]Ataraxic.[/]")
                        break
                    console.print(Rule(style="#394B59"))
                    continue
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
                prov, model, agent = _create_provider(session_id)
                console.print("[dim]Cleared.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/help":
                cmd_registry.list_all()
                cats = cmd_registry.list_by_category()
                for cat, items in cats.items():
                    console.print(f"\n[bold]{cat.upper()}[/]")
                    for c in items:
                        hint = f" {c.arg_hint}" if c.arg_hint else ""
                        aliases = f" ({', '.join(c.aliases)})" if c.aliases else ""
                        console.print(f"  [bold #67D8FF]{c.name}{hint}[/] {c.description}{aliases}")
                console.print()
                continue
            if user == "/model":
                # Step 1: pick provider
                provs = list(_PROVIDERS.keys())
                lines = [f"  [{i}] {_PROVIDERS[p].display_name} ({_PROVIDERS[p].default_model})" for i, p in enumerate(provs)]
                console.print(Panel("\n".join(lines), title="Pick Provider", border_style="#394B59"))
                try:
                    c = await _get_session().prompt_async("Provider #: ", style=PT_STYLE)
                    pi = int(c)
                    if 0 <= pi < len(provs):
                        pid = provs[pi]
                        models = PROVIDER_MODELS.get(pid, [])
                        if len(models) == 1:
                            # Single model — select immediately
                            display = _switch_model(pid, models[0])
                            prov, model, ag = _create_provider(session_id)
                            provider, agent = prov, ag
                            _stats["model"] = display
                            console.print(f"[green]✓ {display}[/]")
                        else:
                            # Step 2: pick model
                            mlines = [f"  [{i}] {m}" for i, m in enumerate(models)]
                            console.print(Panel("\n".join(mlines), title=f"Pick Model — {_PROVIDERS[pid].display_name}", border_style="#394B59"))
                            c2 = await _get_session().prompt_async("Model #: ", style=PT_STYLE)
                            mi = int(c2)
                            if 0 <= mi < len(models):
                                display = _switch_model(pid, models[mi])
                                prov, model, ag = _create_provider(session_id)
                                provider, agent = prov, ag
                                _stats["model"] = display
                                console.print(f"[green]✓ {display}[/]")
                except (ValueError, EOFError, KeyboardInterrupt):
                    console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/sessions":
                from atar_storage.sqlite_store import SqliteStore
                store = SqliteStore()
                sessions = store.list_all()
                if not sessions:
                    console.print("[dim]No sessions.[/]")
                else:
                    lines = [f"  [{i}] {s['title'] or s['session_id'][:12]} ({s.get('message_count','?')} msgs)" for i, s in enumerate(sessions)]
                    console.print(Panel("\n".join(lines), title="Sessions", border_style="#394B59"))
                    try:
                        cs = await _get_session().prompt_async("Pick session: ", style=PT_STYLE)
                        idx = int(cs)
                        if 0 <= idx < len(sessions):
                            s = sessions[idx]
                            data = store.load(s["session_id"])
                            if data:
                                prov, model, ag = _create_provider(session_id)
                                for m in data.get("messages", [])[-20:]:

                                    ag._messages.append(Message(role=m.get("role","user"), content=m.get("content",""), tool_calls=m.get("tool_calls"), tool_call_id=m.get("tool_call_id")))
                                provider, agent = prov, ag
                                console.print(f"[green]✓ {s['title'] or s['session_id'][:12]}[/]")
                    except (ValueError, EOFError, KeyboardInterrupt):
                        pass
                console.print(Rule(style="#394B59"))
                continue
            if user == "/save":
                from atar_storage.sqlite_store import SqliteStore
                store = SqliteStore()
                msgs = [{"role": m.role, "content": m.content, "tool_calls": getattr(m, "tool_calls", None), "tool_call_id": getattr(m, "tool_call_id", None)} for m in agent._messages]
                store.save(session_id, "ATAR Session", msgs)
                # Index for FTS5 search
                from atar_core.session_search import index_session
                text = "\n".join(f"[{m['role']}] {str(m.get('content', ''))[:500]}" for m in msgs)
                index_session(session_id, "ATAR Session", text)
                console.print(f"[green]✓ Saved {len(msgs)} messages ({session_id[:12]})[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user == "/undo" or user.startswith("/undo "):
                n = 1
                if len(user) > 5:
                    with suppress(ValueError):
                        n = int(user[6:].strip())
                restored = agent.undo_last_turn(n)
                if restored:
                    console.print(f"[dim]↺ Restored: {', '.join(restored)}[/]")
                else:
                    console.print("[dim]Nothing to undo — no checkpoints yet.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/retry":
                last = agent.retry_last_turn()
                if last:
                    console.print(f"[dim]↻ Retrying: \"{last[:50]}...\"[/]")
                    _current_task = asyncio.create_task(_agent_turn(last, agent))
                else:
                    console.print("[dim]Nothing to retry.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/checkpoints":
                from atar_tools.tools.checkpoints import list_checkpoints
                cps = list_checkpoints()
                if not cps:
                    console.print("[dim]No checkpoints.[/]")
                else:
                    for cp in cps:
                        console.print(f"  [dim]{cp['id'][:20]}[/] {cp.get('original','?')} ({cp.get('size',0)}B)")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/restore "):
                from atar_tools.tools.checkpoints import restore_checkpoint
                cid = user[len("/restore "):].strip()
                if restore_checkpoint(cid):
                    console.print(f"[green]✓ Restored {cid[:20]}[/]")
                else:
                    console.print(f"[red]Checkpoint not found: {cid[:20]}[/]")
                console.print(Rule(style="#394B59"))
                continue
                console.print(Rule(style="#394B59"))
                continue
            if user == "/code":
                prov2, model2, ag2 = _create_provider(session_id)
                if ag2:
                    ag2.max_turns = 3
                    ag2.system_prompt = "CODE mode. Use terminal, read_file, write_file, git, run_tests."
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Code mode \u00b7 /chat to exit[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/chat":
                prov2, model2, ag2 = _create_provider(session_id)
                if ag2:
                    provider, model, agent = prov2, model2, ag2
                console.print("[dim]Chat mode[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/memory":
                from atar_core.memory import count_active, get_entries
                entries = get_entries()
                if not entries:
                    console.print("[dim]No persistent memories.[/]")
                else:
                    cats: dict[str, list] = {}
                    for e in entries:
                        cats.setdefault(e.category, []).append(e)
                    for cat, items in sorted(cats.items()):
                        console.print(f"\n[bold]{cat}[/]")
                        for e in items:
                            console.print(f"  [{e.id}] [dim]{e.content}[/]")
                console.print(f"\n[dim]{count_active()} active entries[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/memory forget "):
                try:
                    eid = int(user.split()[-1])
                    from atar_core.memory import forget_entry
                    ok = forget_entry(eid)
                    console.print(f"[green]✓ Forgotten #{eid}[/]" if ok else f"[red]Entry #{eid} not found[/]")
                except (ValueError, IndexError):
                    console.print("[red]Usage: /memory forget <id>[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/search "):
                query = user[8:].strip()
                from atar_core.session_search import search_sessions
                results = search_sessions(query)
                if not results:
                    console.print(f"[dim]No sessions matching '{query}'[/]")
                else:
                    for r in results:
                        sid = r["session_id"][:12]
                        summary = r["summary"] or r["snippet"]
                        console.print(f"  [bold]{sid}[/] [dim]{summary[:100]}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/diff full":
                if _last_diff:
                    for d in _last_diff:
                        console.print(d)
                else:
                    console.print("[dim]No diff available. Run a patch operation first.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/backend "):
                name = user[9:].strip()
                try:
                    from atar_core.backends import get_backend, switch_backend
                    b = switch_backend(name)
                    avail = "✓" if b.is_available() else "✗ (unavailable)"
                    console.print(f"[green]{b.name} backend {avail}[/]")
                except ValueError as e:
                    console.print(f"[red]{e}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/backend":
                from atar_core.backends import get_backend
                b = get_backend()
                console.print(f"[dim]Current backend: {b.name}[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user == "/cost":
                from atar_core.background import get_bg_tokens
                from rich.table import Table
                bg = get_bg_tokens()
                table = Table(title="Session Cost Breakdown")
                table.add_column("Category", style="#67D8FF")
                table.add_column("Tokens", style="#FBBF24")
                table.add_column("Cost", style="#4ADE80")
                table.add_row("Main response", f"{_stats['tokens']}/{_stats['tokens_out']}", f"${_stats['cost']:.4f}")
                table.add_row("Background: memory", str(bg.get('memory', 0)), "")
                table.add_row("Background: skill", str(bg.get('skill', 0)), "")
                table.add_row("Turns", str(_stats["turns"]), "")
                table.add_row("Tools used", str(_stats["tools"]), "")
                table.add_row("Model", _stats["model"], "")
                console.print(table)
                console.print(Rule(style="#394B59"))
                continue

            if user.startswith("/tools output "):
                try:
                    tn = int(user[13:].strip())
                    from atar_core.output_truncation import get_full_output
                    full = get_full_output(tn)
                    if full:
                        console.print(f"[bold]Turn {tn} full output:[/]")
                        console.print(full[:10000])
                        if len(full) > 10000:
                            console.print("[dim]... truncated at 10000 chars[/]")
                    else:
                        console.print(f"[dim]No output saved for turn {tn}[/]")
                except ValueError:
                    console.print("[red]Usage: /tools output <turn_number>[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user == "/memory on":
                from atar_core.background import toggle_memory
                toggle_memory()
                console.print("[green]Memory extraction: ON[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/memory off":
                from atar_core.background import toggle_memory
                toggle_memory()
                console.print("[dim]Memory extraction: OFF[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/skills-auto on":
                from atar_core.background import toggle_skills_auto
                toggle_skills_auto()
                console.print("[green]Auto-skill creation: ON[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/skills-auto off":
                from atar_core.background import toggle_skills_auto
                toggle_skills_auto()
                console.print("[dim]Auto-skill creation: OFF[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user == "/init":
                cwd = os.getcwd()
                # Quick project scan
                files = []
                for root, _, filenames in os.walk(cwd):
                    if '.venv' in root or '__pycache__' in root:
                        continue
                    for fn in filenames:
                        if fn.endswith(('.py', '.toml', '.yaml', '.md', '.json')):
                            files.append(os.path.relpath(os.path.join(root, fn), cwd))
                        if len(files) > 50:
                            break
                draft = f"# ATAR Project Context\n\nGenerated from {cwd}\n\n"
                if os.path.exists(os.path.join(cwd, 'pyproject.toml')):
                    draft += "- Python project with pyproject.toml\n"
                if os.path.exists(os.path.join(cwd, 'README.md')):
                    draft += "- Has README.md\n"
                draft += f"- {len(files)} source files detected\n\n"
                draft += "## Commands\n- Test: `uv run pytest`\n- Lint: `uv run ruff check .`\n"
                target = os.path.join(cwd, "ATAR.md")
                with open(target, "w") as f:
                    f.write(draft)
                console.print(f"[green]✓ ATAR.md generated at {target}[/]")
                console.print(f"[dim]{draft[:200]}...[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/compact":
                # Trigger context compaction via agent
                if agent._messages:
                    old = len(agent._messages)
                    # Keep first 2 + last 6 messages
                    if old > 10:
                        agent._messages = agent._messages[:2] + agent._messages[-6:]
                        console.print(f"[dim]Compacted: {old} messages → {len(agent._messages)} (first 2 + last 6)[/]")
                    else:
                        console.print("[dim]Not enough messages to compact.[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user == "/yolo":
                from atar_core.approval import get_approval
                approval = get_approval()
                approval.yolo = not approval.yolo
                status = "ON" if approval.yolo else "OFF"
                console.print(f"[bold yellow]YOLO mode: {status}[/]" + (" ⚠ Auto-approve all tool calls" if approval.yolo else ""))
                console.print(Rule(style="#394B59"))
                continue
            if user == "/permissions" or user.startswith("/permissions set "):
                from atar_core.approval import get_approval
                from rich.table import Table
                approval = get_approval()
                if user.startswith("/permissions set "):
                    parts = user.split()
                    if len(parts) >= 4:
                        tool_name = parts[2]
                        mode = parts[3]
                        if mode in ("always", "ask", "never"):
                            approval.set_tool_mode(tool_name, mode)
                            console.print(f"[green]✓ {tool_name} → {mode}[/]")
                        else:
                            console.print(f"[red]Invalid mode: {mode}. Use always/ask/never.[/]")
                else:
                    table = Table(title="Tool Permissions")
                    table.add_column("Tool", style="#67D8FF")
                    table.add_column("Mode", style="#4ADE80")
                    table.add_column("YOLO", style="#FBBF24")
                    for t in ["write_file", "patch", "terminal", "execute_code"]:
                        mode = approval.tool_modes.get(t, "ask")
                        table.add_row(t, mode, "ON" if approval.yolo else "OFF")
                    console.print(table)
                console.print(Rule(style="#394B59"))
                continue

            if user.startswith("/cron add "):
                parts = user[10:].strip().split(maxsplit=2)
                if len(parts) >= 2:
                    expr, prompt = parts[0], parts[-1]
                    from atar_core.scheduler import add_job
                    jid = add_job(expr, prompt)
                    console.print(f"[green]✓ Job #{jid} scheduled[/]")
                else:
                    console.print("[red]Usage: /cron add <expr> <prompt>[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/cron list":
                from atar_core.scheduler import list_jobs
                jobs = list_jobs()
                if not jobs:
                    console.print("[dim]No scheduled jobs.[/]")
                else:
                    for j in jobs:
                        status = "[green]on[/]" if j.enabled else "[red]off[/]"
                        nxt = time.strftime("%H:%M", time.localtime(j.next_run_at)) if j.next_run_at else "?"
                        console.print(f"  [{j.id}] {status} {nxt} [dim]{j.prompt[:60]}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/cron remove "):
                try:
                    jid = int(user.split()[-1])
                    from atar_core.scheduler import remove_job
                    ok = remove_job(jid)
                    console.print(f"[green]✓ Removed #{jid}[/]" if ok else "[red]Not found[/]")
                except ValueError:
                    console.print("[red]Usage: /cron remove <id>[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/cron pause "):
                try:
                    jid = int(user.split()[-1])
                    from atar_core.scheduler import set_enabled
                    set_enabled(jid, False)
                    console.print(f"[dim]Paused #{jid}[/]")
                except ValueError:
                    console.print("[red]Usage: /cron pause <id>[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/cron resume "):
                try:
                    jid = int(user.split()[-1])
                    from atar_core.scheduler import set_enabled
                    set_enabled(jid, True)
                    console.print(f"[green]Resumed #{jid}[/]")
                except ValueError:
                    console.print("[red]Usage: /cron resume <id>[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user == "/skills":
                from atar_core.skills import get_skill_manager
                mgr = get_skill_manager()
                active = mgr.list_active()
                pending = mgr.list_pending()
                if active:
                    console.print("\n[bold]Active:[/]")
                    for s in active:
                        console.print(f"  {s.name} [dim]used {s.times_used}x, {s.description}[/]")
                if pending:
                    console.print("\n[bold]Pending:[/]")
                    for s in pending:
                        console.print(f"  {s.name} [dim]{s.description}[/]")
                if not active and not pending:
                    console.print("[dim]No skills yet.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/skills review "):
                name = user.split(maxsplit=2)[-1].strip()
                from atar_core.skills import get_skill_manager
                mgr = get_skill_manager()
                content = mgr.load_skill_md(name)
                if not content:
                    console.print(f"[red]No pending skill '{name}'[/]")
                else:
                    console.print(Panel(content[:2000], title=f"Review: {name}", border_style="#E8C07D"))
                    try:
                        ans = await _get_session().prompt_async(
                            HTML("<yellow>Approve? (y/n)</yellow> "), style=PT_STYLE
                        )
                        if ans.strip().lower() in ("y", "yes"):
                            ok = mgr.review(name, approve=True)
                            console.print(f"[green]✓ {name} promoted[/]" if ok else "[red]Failed[/]")
                        else:
                            mgr.review(name, approve=False)
                            console.print("[dim]Rejected.[/]")
                    except (EOFError, KeyboardInterrupt):
                        console.print("[dim]Cancelled.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/skills delete "):
                name = user.split(maxsplit=2)[-1].strip()
                from atar_core.skills import get_skill_manager
                mgr = get_skill_manager()
                ok = mgr.delete(name)
                console.print(f"[green]✓ Archived {name}[/]" if ok else f"[red]Skill '{name}' not found[/]")
                console.print(Rule(style="#394B59"))
                continue

            if user.startswith("/remember "):
                from atar_core.memory import add_memory
                text = user[len("/remember "):].strip()
                if text:
                    add_memory(text, category="user")
                    console.print(f"[dim]Saved: {text[:80]}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/compress":
                from atar_core.compress import compress_history
                console.print("[dim]Compressing context...[/]")
                result = await compress_history(agent)
                console.print(f"[green]✓ {result}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/toolset":
                from atar_tools.toolsets import enabled_toolsets
                sets = enabled_toolsets()
                console.print(f"[dim]Active: {', '.join(sets)}[/]")
                console.print("[dim]Available: safe file terminal web browser sessions[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/toolset "):
                ts = user[len("/toolset "):].strip()
                console.print(f"[dim]Toolset '{ts}' activated.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/personality":
                console.print("[dim]Available: default[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/personality "):
                name = user[len("/personality "):].strip()
                console.print(f"[dim]Personality '{name}' loaded.[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user == "/usage":
                stats = _stats
                console.print(f"[dim]Tokens: {stats.get('text_chars',0)} chars[/]")
                console.print(f"[dim]Turns: {stats.get('turns',0)}[/]")
                console.print(f"[dim]Tools executed: {stats.get('tools',0)}[/]")
                console.print(Rule(style="#394B59"))
                continue
            if user.startswith("/insights"):
                console.print("[dim]Insights across sessions (last 7 days):[/]")
                console.print("[dim]No historical data yet — run more sessions first.[/]")
                console.print(Rule(style="#394B59"))
                continue


            # Resolve @file references in user input
            if "@" in user:
                import re
                for match in re.finditer(r'@([^\s]+)', user):
                    ref_path = match.group(1)
                    full_path = os.path.join(os.getcwd(), ref_path)
                    if os.path.isfile(full_path):
                        try:
                            with open(full_path) as rf:
                                fc = rf.read()[:3000]
                            user = user.replace(f"@{ref_path}", f"[{ref_path}]")
                            user += f"\n[File content from @{ref_path}]:\n{fc}\n"
                        except Exception:
                            pass

            # Busy-mode handling
            is_running = _current_task and not _current_task.done()
            if is_running:
                mode = get_busy_mode()
                if mode == "queue":
                    _pending_queue.append(user)
                    console.print("[dim]Queued (will run after current turn)[/]")
                    console.print(Rule(style="#394B59"))
                    continue
                elif mode == "steer":
                    # Inject into current run agent context
                    agent._messages.append(Message(role="user", content=f"[Steer] {user.strip()}"))
                    console.print(f"[dim]↳ Steered: {user[:60]}[/]")
                    console.print(Rule(style="#394B59"))
                    continue
                # interrupt is default — cancel and start fresh
                if should_show_busy_hint():
                    console.print("[dim]Tip: Use /busy queue or /busy steer to change behavior when busy[/]")
                    mark_busy_hint_shown()
                _current_task.cancel()
            _current_task = asyncio.create_task(_agent_turn(user, agent))
            with suppress(asyncio.CancelledError):
                await _current_task

    asyncio.run(_run())


if __name__ == "__main__":
    run_repl()
