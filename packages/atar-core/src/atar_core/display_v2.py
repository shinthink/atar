"""ATAR display engine — Claude/Hermes-class styling.

Thinking animations, tool cards, modern status bar, response panels.
"""

from __future__ import annotations

import time
from typing import Any

# ═══════════════════════════════════════════════════════════════════════════
# TOOL ICONS + COLORS — per-category styling
# ═══════════════════════════════════════════════════════════════════════════

TOOL_STYLE: dict[str, dict[str, str]] = {
    "read_file":       {"icon": "📖", "color": "#60A5FA", "label": "reading"},
    "write_file":      {"icon": "✍️", "color": "#34D399", "label": "writing"},
    "patch":           {"icon": "🔧", "color": "#FBBF24", "label": "patching"},
    "terminal":        {"icon": "💻", "color": "#A78BFA", "label": "running"},
    "web_search":      {"icon": "🔍", "color": "#38BDF8", "label": "searching"},
    "web_fetch":       {"icon": "📄", "color": "#38BDF8", "label": "fetching"},
    "git":             {"icon": "🔀", "color": "#F472B6", "label": "git"},
    "github":          {"icon": "🐙", "color": "#F472B6", "label": "github"},
    "search_files":    {"icon": "🔎", "color": "#60A5FA", "label": "searching"},
    "browser":         {"icon": "🌐", "color": "#38BDF8", "label": "browsing"},
    "real_browser":    {"icon": "🌐", "color": "#38BDF8", "label": "browsing"},
    "execute_code":    {"icon": "⚡", "color": "#FB923C", "label": "executing"},
    "cronjob":         {"icon": "⏰", "color": "#A78BFA", "label": "scheduling"},
    "delegate_task":   {"icon": "👥", "color": "#34D399", "label": "delegating"},
    "load_skill":      {"icon": "📦", "color": "#FBBF24", "label": "loading"},
    "run_tests":       {"icon": "🧪", "color": "#34D399", "label": "testing"},
    "memory_add":      {"icon": "🧠", "color": "#C084FC", "label": "remembering"},
    "memory_list":     {"icon": "🧠", "color": "#C084FC", "label": "recalling"},
    "memory_semantic": {"icon": "🧠", "color": "#C084FC", "label": "searching"},
    "session_search":  {"icon": "🔍", "color": "#60A5FA", "label": "searching"},
    "session_resume":  {"icon": "↩️", "color": "#60A5FA", "label": "resuming"},
    "analyze_image":   {"icon": "🖼️", "color": "#FB923C", "label": "analyzing"},
    "weather":         {"icon": "🌤️", "color": "#38BDF8", "label": "checking"},
    "stocks":          {"icon": "📈", "color": "#34D399", "label": "checking"},
    "maps":            {"icon": "🗺️", "color": "#FBBF24", "label": "mapping"},
    "pdf":             {"icon": "📑", "color": "#F87171", "label": "reading"},
}


def tool_icon(name: str) -> str:
    return TOOL_STYLE.get(name, {}).get("icon", "🔧")


def tool_color(name: str) -> str:
    return TOOL_STYLE.get(name, {}).get("color", "#9CA3AF")


def tool_label(name: str) -> str:
    return TOOL_STYLE.get(name, {}).get("label", name.replace("_", " "))


# ═══════════════════════════════════════════════════════════════════════════
# THINKING ANIMATION — Claude Code style
# ═══════════════════════════════════════════════════════════════════════════

class ThinkingAnimator:
    """Claude Code-style animated thinking indicator."""

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _LABELS = [
        "thinking...",
        "considering...",
        "analyzing...",
        "reasoning...",
        "processing...",
        "generating...",
        "evaluating...",
        "composing...",
    ]

    def __init__(self) -> None:
        self._i = 0
        self._label_idx = 0
        self._label_switch = 0
        self._start = time.monotonic()

    def tick(self) -> str:
        self._i = (self._i + 1) % len(self._FRAMES)
        self._label_switch += 1
        if self._label_switch >= 15:
            self._label_switch = 0
            self._label_idx = (self._label_idx + 1) % len(self._LABELS)
        elapsed = time.monotonic() - self._start
        frame = self._FRAMES[self._i]
        label = self._LABELS[self._label_idx]
        return f"  {frame} {label} ({elapsed:.1f}s)"

    def start(self) -> str:
        self._start = time.monotonic()
        return self.tick()

    def finish(self) -> str:
        elapsed = time.monotonic() - self._start
        return f"  ✓ done ({elapsed:.1f}s)"


# ═══════════════════════════════════════════════════════════════════════════
# TOOL CALL CARDS — colored panels like Hermes
# ═══════════════════════════════════════════════════════════════════════════

def format_tool_progress(tool_name: str, arguments: dict[str, Any]) -> str:
    """Format a tool call as a colored progress card."""
    icon = tool_icon(tool_name)
    color = tool_color(tool_name)
    label = tool_label(tool_name)
    args_preview = _format_args_preview(tool_name, arguments)

    return (
        f"  [{color}]┊[/] [{color}]{icon}[/] [{color} bold]{label}[/]"
        f" [dim]{args_preview}[/]"
    )


def format_tool_result(tool_name: str, output: str) -> str:
    """Format a tool result in the feed."""
    if not output:
        output = "(no output)"
    preview = output.strip()[:80].replace("\n", " ")
    return f"  [dim]  └─ {preview}{'...' if len(output) > 80 else ''}[/]"


def _format_args_preview(tool_name: str, args: dict) -> str:
    """Format a clean argument preview based on tool type."""
    if tool_name in ("read_file", "write_file", "patch"):
        return args.get("path", args.get("file_path", ""))[:50]
    if tool_name == "terminal":
        cmd = args.get("command", "")[:50]
        return cmd.replace("\n", " ")
    if tool_name in ("web_search",):
        return args.get("query", "")[:50]
    if tool_name in ("web_fetch", "browser", "real_browser"):
        return args.get("url", "")[:50]
    if tool_name == "git":
        return args.get("action", "")[:30]
    if tool_name == "memory_add":
        return args.get("content", "")[:50]
    if tool_name == "weather":
        return args.get("city", "")[:30]
    if tool_name == "stocks":
        return args.get("symbol", "")[:10]
    if tool_name == "maps":
        return args.get("query", "")[:40]
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# MODERN STATUS BAR — Claude/Hermes style
# ═══════════════════════════════════════════════════════════════════════════

def status_bar_modern(
    model: str = "",
    tokens_used: int = 0,
    max_tokens: int = 128000,
    turns: int = 0,
    tools: int = 0,
    cost: float = 0,
    elapsed: float = 0,
) -> str:
    """Polished status bar like Claude Code bottom line."""

    # Model icon + name
    model_icon = _model_icon(model)
    model_str = f"{model_icon} {model}" if model else "ATAR"

    # Token meter
    pct = min(tokens_used / max_tokens, 1.0) if max_tokens else 0
    bar_width = 8
    filled = int(pct * bar_width)
    tok_bar = "█" * filled + "░" * (bar_width - filled)
    if pct < 0.5:
        bar_color = "#4ADE80"
    elif pct < 0.8:
        bar_color = "#FBBF24"
    else:
        bar_color = "#F87171"

    tokens_str = (
        f"[{bar_color}]{tok_bar}[/] "
        f"{tokens_used / 1000:.1f}K/{max_tokens / 1000:.0f}K"
        if max_tokens >= 1000
        else f"{tokens_used}/{max_tokens}"
    )

    # Cost
    cost_str = f"${cost:.3f}" if cost > 0 else "$0"

    # Time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    time_str = f"{mins}m{secs:02d}s" if mins > 0 else f"{secs}s"

    # Sections
    parts = [
        f"[bold]{model_str}[/]",
        tokens_str,
    ]
    if turns > 0:
        parts.append(f"↻{turns}")
    if tools > 0:
        parts.append(f"⚒{tools}")
    parts.append(cost_str)
    parts.append(time_str)

    return " │ ".join(parts)


def _model_icon(model: str) -> str:
    """Get model icon based on provider."""
    model_lower = model.lower()
    if "deepseek" in model_lower:
        return "🔷"
    if "openai" in model_lower or "gpt" in model_lower:
        return "🟢"
    if "claude" in model_lower or "anthropic" in model_lower:
        return "🟠"
    if "ollama" in model_lower:
        return "🦙"
    if "openrouter" in model_lower:
        return "🔀"
    return "🤖"


# ═══════════════════════════════════════════════════════════════════════════
# RESPONSE PANELS — cleaner, more modern
# ═══════════════════════════════════════════════════════════════════════════

def format_response_panel(text: str, model: str = "", elapsed: float = 0) -> str:
    """Format the AI response in a clean panel."""
    if not text.strip():
        return ""

    lines = text.strip().split("\n")

    # Build panel
    result = []
    result.append("")

    for line in lines:
        # Code blocks
        if line.startswith("```"):
            continue  # Markdown code blocks handled by Rich separately
        if line.startswith("##"):
            result.append(f"[bold underline]{line[2:].strip()}[/]")
        elif line.startswith("#"):
            result.append(f"[bold]{line[1:].strip()}[/]")
        elif line.startswith("- ") or line.startswith("* "):
            result.append(f"  • {line[2:]}")
        else:
            result.append(line)

    # Footer
    elapsed_str = f"{elapsed:.1f}s" if elapsed else ""
    footer = "[dim]─ ATAR[/]"
    if elapsed_str and model:
        footer += f"[dim] · {model} · {elapsed_str}[/]"
    elif model:
        footer += f"[dim] · {model}[/]"

    result.append("")
    result.append(footer)

    return "\n".join(result)


# ═══════════════════════════════════════════════════════════════════════════
# COMPACT BANNER
# ═══════════════════════════════════════════════════════════════════════════

COMPACT_LOGO = r"""
  █████╗ ████████╗ █████╗ ██████╗
 ██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗
 ███████║   ██║   ███████║██████╔╝
 ██╔══██║   ██║   ██╔══██║██╔══██╗
 ██║  ██║   ██║   ██║  ██║██║  ██║
 ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝
     Clarity in Complexity.
"""


# ═══════════════════════════════════════════════════════════════════════════
# THEME COLORS
# ═══════════════════════════════════════════════════════════════════════════

THEMES = {
    "atar": {
        "primary": "#4FC3F7",
        "success": "#4ADE80",
        "warning": "#FBBF24",
        "error": "#F87171",
        "dim": "#6B7280",
        "border": "#374151",
        "bg": "#1F2937",
    },
    "monochrome": {
        "primary": "#9CA3AF",
        "success": "#D1D5DB",
        "warning": "#9CA3AF",
        "error": "#EF4444",
        "dim": "#6B7280",
        "border": "#4B5563",
        "bg": "#111827",
    },
    "forest": {
        "primary": "#34D399",
        "success": "#6EE7B7",
        "warning": "#FBBF24",
        "error": "#F87171",
        "dim": "#6B7280",
        "border": "#065F46",
        "bg": "#064E3B",
    },
    "ocean": {
        "primary": "#38BDF8",
        "success": "#4ADE80",
        "warning": "#FBBF24",
        "error": "#F87171",
        "dim": "#6B7280",
        "border": "#1E3A5F",
        "bg": "#0F172A",
    },
}


def get_theme(name: str = "atar") -> dict:
    return THEMES.get(name, THEMES["atar"])


# ── Cost calculation (unchanged) ──

PROVIDER_PRICING: dict[str, tuple[float, float]] = {
    "deepseek": (0.435, 0.87),
    "openai": (2.50, 10.00),
    "anthropic": (3.00, 15.00),
    "openrouter": (0.435, 0.87),
    "zai": (0, 0),
    "custom": (0, 0),
    "ollama": (0, 0),
}


def calculate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    provider = "deepseek"
    for p in PROVIDER_PRICING:
        if p in model.lower():
            provider = p
            break
    pin, pout = PROVIDER_PRICING.get(provider, (0, 0))
    return (tokens_in * pin + tokens_out * pout) / 1_000_000
