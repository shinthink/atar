"""ATAR display engine — status bar, tool feed, thinking animation."""

from __future__ import annotations

import time

# ── Tool icons (one per tool category) ──
TOOL_ICONS = {
    "read_file": "\U0001f4d6",       # 📖
    "write_file": "\u270d\ufe0f",   # ✍️
    "terminal": "\U0001f4bb",        # 💻
    "web_search": "\U0001f50d",      # 🔍
    "web_fetch": "\U0001f4c4",       # 📄
    "git": "\U0001f500",             # 🔀
    "run_tests": "\u2714\ufe0f",     # ✔️
    "patch": "\U0001f527",           # 🔧
    "search_files": "\U0001f50e",    # 🔎
    "browser": "\U0001f310",         # 🌐
    "execute_code": "\u2699\ufe0f",  # ⚙️
    "cronjob": "\u23f0",             # ⏰
    "delegate_task": "\U0001f465",   # 👥
    "load_skill": "\U0001f4e6",      # 📦
    "session_search": "\U0001f50d",  # 🔍
    "session_resume": "\u21a9\ufe0f", # ↩️
}

# ── Context bar thresholds ──
def context_bar(tokens_used: int, max_tokens: int = 128000) -> str:
    if max_tokens <= 0:
        max_tokens = 128000
    pct = min(tokens_used / max_tokens, 1.0)
    filled = int(pct * 10)
    bar = "\u2588" * filled + "\u2591" * (10 - filled)
    if pct < 0.5:
        color = "#4ADE80"
    elif pct < 0.8:
        color = "#FBBF24"
    elif pct < 0.95:
        color = "#FB923C"
    else:
        color = "#F87171"
    pct_str = f"{tokens_used / 1000:.1f}K"
    max_str = f"{max_tokens / 1000:.0f}K" if max_tokens >= 1000 else str(max_tokens)
    return f"{pct_str}/{max_str} [{bar}] {int(pct*100)}%", color


# ── Pricing model (per 1M tokens, input/output) ──
PROVIDER_PRICING: dict[str, tuple[float, float]] = {
    "deepseek": (0.435, 0.87),        # deepseek-v4-pro per 1M
    "openai": (2.50, 10.00),          # gpt-5.6 approximate
    "anthropic": (3.00, 15.00),       # claude-sonnet-4 approximate
    "openrouter": (0.435, 0.87),      # pass-through
    "zai": (0, 0),
    "custom": (0, 0),
}

def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate USD cost from provider pricing."""
    # Try to match provider from model name
    provider = "deepseek"
    if "claude" in model.lower():
        provider = "anthropic"
    elif "gpt" in model.lower():
        provider = "openai"
    elif "openrouter" in model.lower():
        provider = "openrouter"
    prices = PROVIDER_PRICING.get(provider, (0, 0))
    return (tokens_in * prices[0] + tokens_out * prices[1]) / 1_000_000


# ── Thinking animation ──
THINKING_FRAMES = ["◜", "◝", "◞", "◟"]
THINKING_WORDS = ["thinking", "pondering", "processing", "computing"]
THINKING_INTERVAL = 0.2  # seconds between frame updates


class ThinkingAnimator:
    """Rotating kaomoji-style thinking indicator."""
    def __init__(self) -> None:
        self._frame = 0
        self._word = 0
        self._start: float = 0.0
        self.running = False

    def start(self) -> str:
        self._start = time.time()
        self.running = True
        return self._render()

    def tick(self) -> str:
        self._frame = (self._frame + 1) % len(THINKING_FRAMES)
        if self._frame == 0:
            self._word = (self._word + 1) % len(THINKING_WORDS)
        return self._render()

    def _render(self) -> str:
        elapsed = time.time() - self._start
        frame = THINKING_FRAMES[self._frame]
        word = THINKING_WORDS[self._word]
        return f"{frame} {word}... ({elapsed:.1f}s)"

    @staticmethod
    def static_line() -> str:
        return "●  thinking..."


# ── Verbose levels ──
VERBOSE_OFF = 0   # no tool output
VERBOSE_NEW = 1   # new tools show
VERBOSE_ALL = 2   # all tools
VERBOSE_FULL = 3  # full detail

_verbose_level = VERBOSE_NEW

def get_verbose() -> int:
    return _verbose_level

def cycle_verbose() -> str:
    global _verbose_level
    names = {0: "off", 1: "new", 2: "all", 3: "verbose"}
    _verbose_level = (_verbose_level + 1) % 4
    return names[_verbose_level]
