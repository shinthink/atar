"""ATAR theme engine — YAML-based skins with NO_COLOR and high-contrast support."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ThemeColors:
    primary: str = "#67D8FF"
    secondary: str = "#7AA2F7"
    accent: str = "#B4F1FF"
    text: str = "default"
    muted: str = "#7F8C98"
    success: str = "#78D6A5"
    warning: str = "#E8C07D"
    error: str = "#F08C8C"
    border: str = "#394B59"
    dim_border: str = "#25313B"
    bg: str = "default"
    prompt: str = "#67D8FF bold"


@dataclass
class ThemeLayout:
    response_style: str = "rule"  # rule | rail | border
    banner: str = "compact"  # compact | full | none
    show_status_bar: bool = True
    show_tool_elapsed: bool = True
    tool_prefix: str = "┊"
    prompt_symbol: str = "›"


@dataclass
class ThemeSpinner:
    frames: list[str] = field(default_factory=lambda: ["◌", "◔", "◑", "◕", "●"])
    verbs: list[str] = field(default_factory=lambda: ["clarifying", "examining", "verifying", "integrating"])


@dataclass
class Theme:
    name: str
    colors: ThemeColors = field(default_factory=ThemeColors)
    layout: ThemeLayout = field(default_factory=ThemeLayout)
    spinner: ThemeSpinner = field(default_factory=ThemeSpinner)


# ── Built-in themes ──

def _atar_theme() -> Theme:
    return Theme(
        name="atar",
        colors=ThemeColors(),
        layout=ThemeLayout(),
        spinner=ThemeSpinner(),
    )


def _monochrome_theme() -> Theme:
    return Theme(
        name="monochrome",
        colors=ThemeColors(
            primary="white", secondary="white", accent="white",
            text="white", muted="dim white", success="white",
            warning="white", error="white", border="white",
            dim_border="dim white", bg="default", prompt="white bold",
        ),
        layout=ThemeLayout(response_style="rule"),
        spinner=ThemeSpinner(frames=["...", " ..", "  .", " .."], verbs=["working"]),
    )


def _highcontrast_theme() -> Theme:
    return Theme(
        name="high-contrast",
        colors=ThemeColors(
            primary="#00FFFF", secondary="#FFD700", accent="#00FF00",
            text="white", muted="#AAAAAA", success="#00FF00",
            warning="#FFFF00", error="#FF0000", border="#FFFFFF",
            dim_border="#888888", bg="default", prompt="cyan bold",
        ),
        layout=ThemeLayout(),
        spinner=ThemeSpinner(),
    )


BUILTIN: dict[str, Theme] = {
    "atar": _atar_theme(),
    "monochrome": _monochrome_theme(),
    "high-contrast": _highcontrast_theme(),
}


def _detect_theme() -> str:
    """Detect which theme to use based on environment."""
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return "monochrome"
    return "atar"


def load_theme(name: str | None = None) -> Theme:
    """Load theme by name, environment, or config."""
    name = name or _detect_theme()
    return BUILTIN.get(name, BUILTIN["atar"])


def current_theme() -> Theme:
    """Get the currently active theme."""
    return load_theme()


def theme_to_rich_style(theme: Theme) -> dict[str, str]:
    """Convert Theme to Rich Style dict."""
    c = theme.colors
    return {
        "prompt": c.prompt,
        "separator": c.border,
        "toolbar": f"bg:{c.bg} {c.muted}",
    }


def theme_to_pt_style(theme: Theme) -> Any:
    """Convert Theme to prompt_toolkit Style."""
    from prompt_toolkit.styles import Style
    c = theme.colors
    return Style.from_dict({
        "prompt": c.prompt,
        "toolbar": f"bg:#1a1a2e {c.muted}",
        "separator": c.dim_border,
    })
