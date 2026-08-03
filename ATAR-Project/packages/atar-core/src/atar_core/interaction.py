"""ATAR interaction modes — busy input, background sessions, session resume."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from atar_core.paths import _atar_home as atar_home


# ── Busy input mode ──
BUSY_MODES = ("interrupt", "queue", "steer")
_busy_mode = "interrupt"
_busy_hint_shown = False
CONFIG_PATH = os.path.join(atar_home(), "config.json")


def _read_config_flag(key: str, default: bool = False) -> bool:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f).get("display", {}).get(key, default)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_config_flag(key: str, value: bool) -> None:
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = {}
    cfg.setdefault("display", {})[key] = value
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


def get_busy_mode() -> str:
    return _busy_mode


def set_busy_mode(mode: str) -> str:
    global _busy_mode
    if mode in BUSY_MODES:
        _busy_mode = mode
    return _busy_mode


def should_show_busy_hint() -> bool:
    if _busy_hint_shown:
        return False
    return not _read_config_flag("busy_hint_shown", False)


def mark_busy_hint_shown() -> None:
    global _busy_hint_shown
    _busy_hint_shown = True
    _write_config_flag("busy_hint_shown", True)


def handle_busy_input(user: str, is_running: bool) -> tuple[str, bool]:
    """Returns (action, should_start_turn). Action: 'interrupt'/'queue'/'steer'."""
    mode = _busy_mode
    if mode == "steer" and (not is_running):
        mode = "queue"  # fallback 1: no run in progress
    return mode, mode in ("interrupt", "steer")


# ── Background sessions ──
@dataclass
class BackgroundTask:
    task_id: str
    prompt: str
    result: Optional[str] = None
    done: bool = False
    start_time: float = 0.0

_bg_tasks: dict[str, BackgroundTask] = {}
_bg_results: list[str] = []  # pending results to display


def start_background(prompt: str, agent_factory) -> str:
    """Spawn background agent session. Returns task_id."""
    task_id = f"bg_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    task = BackgroundTask(task_id=task_id, prompt=prompt, start_time=time.time())
    _bg_tasks[task_id] = task

    def _run():
        try:
            agent = agent_factory()
            # Use read-only tools only for safety
            agent.interactive = False  # no approval prompts in bg
            loop = asyncio.new_event_loop()
            result = loop.run_until_complete(agent.run(prompt))
            task.result = result.final_text if hasattr(result, "final_text") else str(result)
        except Exception as e:
            task.result = f"Error: {e}"
        task.done = True
        _bg_results.append(task.task_id)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return task_id


def get_pending_bg_results() -> list[BackgroundTask]:
    """Get completed background tasks whose results haven't been displayed."""
    results = []
    for tid in list(_bg_results):
        if tid in _bg_tasks and _bg_tasks[tid].done:
            results.append(_bg_tasks[tid])
            _bg_results.remove(tid)
    return results


def get_active_bg_count() -> int:
    return sum(1 for t in _bg_tasks.values() if not t.done)


# ── Session resume recap ──
def generate_recap(session_data: dict) -> str | None:
    """Pure local computation — no LLM call. Returns recap text or None."""
    msgs = session_data.get("messages", [])
    if not msgs:
        return None
    turns = sum(1 for m in msgs if m.get("role") == "user")
    tools_used = set()
    files_touched = []
    for m in msgs:
        if m.get("role") == "tool":
            tools_used.add(m.get("name", "?"))
        if m.get("role") == "assistant" and "write_file" in str(m.get("content", "")):
            for line in str(m.get("content", "")).split("\n"):
                if line.strip().startswith("/"):
                    files_touched.append(line.strip().split()[0])

    last_user = ""
    last_assistant = ""
    for m in reversed(msgs):
        if m.get("role") == "user" and not last_user:
            last_user = str(m.get("content", ""))[:100]
        if m.get("role") == "assistant" and not last_assistant:
            last_assistant = str(m.get("content", ""))[:100]

    recap = f"Turns: {turns} | Tools: {', '.join(sorted(tools_used)[:5]) or 'none'}"
    if files_touched:
        recap += f" | Files: {', '.join(files_touched[:3])}"
    if last_user:
        recap += f"\nLast: {last_user}"
    return recap
