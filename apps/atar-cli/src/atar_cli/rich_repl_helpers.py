"""ATAR REPL helpers — pure functions extracted from rich_repl.py for testability."""

from __future__ import annotations

import json
import os
import time

# ── Tool risk classification ──

TOOL_RISK_MAP: dict[str, tuple[str, str]] = {
    "read_file": ("Read-only", "#4ADE80"),
    "search_files": ("Read-only", "#4ADE80"),
    "session_search": ("Read-only", "#4ADE80"),
    "session_resume": ("Read-only", "#4ADE80"),
    "git": ("Read-only", "#4ADE80"),
    "web_search": ("Network", "#FBBF24"),
    "web_fetch": ("Network", "#FBBF24"),
    "browser": ("Network", "#FBBF24"),
    "write_file": ("Write", "#F87171"),
    "patch": ("Write", "#F87171"),
    "terminal": ("Execute", "#EF4444"),
    "run_tests": ("Execute", "#EF4444"),
    "execute_code": ("Execute", "#EF4444"),
    "cronjob": ("Execute", "#EF4444"),
    "delegate_task": ("Execute", "#EF4444"),
}


def tool_risk(tool_name: str) -> tuple[str, str]:
    """Return (risk_label, color) for a tool."""
    return TOOL_RISK_MAP.get(tool_name, ("Unknown", "#9CA3AF"))


# ── BASE_PROMPT — static system prompt template ──

BASE_PROMPT = (
    "You are ATAR, an autonomous agent with tools: web_search, web_fetch, read_file, write_file, terminal.\n"
    "Platform: Linux. Shell: bash.\n"
    "CRITICAL:\n"
    "- For research — call web_search IMMEDIATELY. No explanations first.\n"
    "- For coding — call write_file IMMEDIATELY. Never say 'Saya akan buat' or 'let me'. Just act.\n"
    "- For simple chat/greetings — respond directly.\n"
    "- Use Linux commands (xdg-open, rm, ls, grep, etc). Never suggest open/start.\n"
    "- Never prefix your response with 'I will' or 'Saya akan'. Just use the tool.\n"
    "- Never assume or fabricate the user's name. Only use their name if they explicitly tell you.\n"
    "- Be concise. One-sentence answers preferred.\n"
    "- Match the user's language."
)


# ── Config helpers ──

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


def switch_model_config(provider_id: str, model_id: str) -> str:
    """Switch to a specific provider+model. Returns display string."""
    from atar_core.provider_registry import get_provider
    prof = get_provider(provider_id)
    name = prof.display_name if prof else provider_id
    cfg = _read_config()
    cfg["provider"] = provider_id
    cfg["model"] = model_id
    _save_config(cfg)
    return f"{name} — {model_id}"


# ── CWD shortening ──

def short_cwd(cwd: str | None = None) -> str:
    """Shorten current working directory for display."""
    cwd = cwd or os.getcwd()
    short = cwd.replace(os.path.expanduser("~"), "~")
    if len(short) > 50:
        short = "..." + short[-47:]
    return short


# ── Context bar computation ──

def compute_context_bar(tokens_used: int, max_tokens: int = 128000) -> str:
    """Compute the context bar string from token stats."""
    if max_tokens <= 0:
        max_tokens = 128000
    pct = min(tokens_used / max_tokens, 1.0)
    width = 10
    filled = int(pct * width)
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    return f" {tokens_used/1000:.1f}K/{max_tokens//1000}K [{bar}] {pct*100:.0f}%"


# ── Status bar assembly ──

def compute_status_bar(
    *,
    model: str = "deepseek-chat",
    turns: int = 0,
    tools: int = 0,
    tokens: int = 0,
    tokens_out: int = 0,
    cost: float = 0.0,
    start_time: float | None = None,
    compressions: int = 0,
    background_tasks: int = 0,
    term_width: int = 80,
    active_bg_count: int = 0,
) -> str:
    """Compute the status bar string. Pure function — no global state."""
    if start_time is None:
        start_time = time.time()
    elapsed = int(time.time() - start_time)
    h, r = divmod(elapsed, 3600)
    m, s = divmod(r, 60)
    duration = f"{h}h{m}m" if h else f"{m}m{s}s"
    ctx = compute_context_bar(tokens + tokens_out, 128000)
    c = f"${cost:.2f}" if cost > 0 else "$0"
    badges = []
    if compressions:
        badges.append(f"\U0001f5dc {compressions}")
    if active_bg_count > 0:
        badges.append(f"\u25b6 {background_tasks}")
    bg = " " + " ".join(badges) if badges else ""
    if term_width >= 76:
        return f"\u25c6 {model} \u2502 {ctx} \u2502 turns {turns} \u2502 tools {tools} \u2502 {c} \u2502 {duration}{bg}"
    elif term_width >= 52:
        return f"\u25c6 {model} \u2502 {ctx} \u2502 {c} \u2502 {duration}{bg}"
    else:
        return f"\u25c6 {model} \u2502 {duration}{bg}"


# ── Runtime stats helper ──

class ReplStats:
    """Mutable stats container for the REPL session."""

    def __init__(self) -> None:
        self.turns: int = 0
        self.tools: int = 0
        self.tokens: int = 0
        self.tokens_out: int = 0
        self.start_time: float | None = None
        self.model: str = "deepseek-chat"
        self.compressions: int = 0
        self.background_tasks: int = 0
        self.cost: float = 0.0
        self.text_chars: int = 0

    def to_dict(self) -> dict:
        return {
            "turns": self.turns,
            "tools": self.tools,
            "tokens": self.tokens,
            "tokens_out": self.tokens_out,
            "model": self.model,
            "cost": self.cost,
            "start_time": self.start_time,
            "compressions": self.compressions,
            "background_tasks": self.background_tasks,
        }
