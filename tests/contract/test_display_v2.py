"""Tests for display_v2 styling engine."""

from __future__ import annotations


class TestToolStyle:
    def test_tool_icon_known(self) -> None:
        from atar_core.display_v2 import tool_icon
        assert tool_icon("terminal") == "💻"
        assert tool_icon("read_file") == "📖"
        assert tool_icon("unknown_tool") == "🔧"

    def test_tool_color_known(self) -> None:
        from atar_core.display_v2 import tool_color
        assert tool_color("terminal") == "#A78BFA"
        assert tool_color("write_file") == "#34D399"

    def test_tool_label(self) -> None:
        from atar_core.display_v2 import tool_label
        assert tool_label("terminal") == "running"
        assert tool_label("unknown") == "unknown"


class TestThinkingAnimator:
    def test_animator_ticks(self) -> None:
        from atar_core.display_v2 import ThinkingAnimator
        a = ThinkingAnimator()
        tick = a.tick()
        assert "thinking" in tick.lower() or "processing" in tick.lower()

    def test_animator_finish(self) -> None:
        from atar_core.display_v2 import ThinkingAnimator
        a = ThinkingAnimator()
        a.tick()
        finish = a.finish()
        assert "done" in finish


class TestStatusBar:
    def test_status_bar_default(self) -> None:
        from atar_core.display_v2 import status_bar_modern
        bar = status_bar_modern()
        assert "│" in bar or len(bar) > 0

    def test_status_bar_with_data(self) -> None:
        from atar_core.display_v2 import status_bar_modern
        bar = status_bar_modern(
            model="deepseek-chat",
            tokens_used=5000,
            max_tokens=128000,
            turns=3,
            tools=5,
            cost=0.002,
            elapsed=45,
        )
        assert "deepseek" in bar.lower()
        assert "45s" in bar or "0m" in bar

    def test_model_icon(self) -> None:
        from atar_core.display_v2 import _model_icon
        assert _model_icon("deepseek-chat") == "🔷"
        assert _model_icon("gpt-5.6") == "🟢"
        assert _model_icon("ollama-llama3") == "🦙"


class TestToolProgress:
    def test_format_tool_progress(self) -> None:
        from atar_core.display_v2 import format_tool_progress
        result = format_tool_progress("terminal", {"command": "ls -la"})
        assert "💻" in result
        assert "ls -la" in result or "running" in result.lower()

    def test_format_tool_result(self) -> None:
        from atar_core.display_v2 import format_tool_result
        result = format_tool_result("terminal", "hello world")
        assert "hello" in result


class TestThemes:
    def test_themes_exist(self) -> None:
        from atar_core.display_v2 import THEMES
        assert "atar" in THEMES
        assert "monochrome" in THEMES
        assert "forest" in THEMES
        assert "ocean" in THEMES

    def test_get_theme(self) -> None:
        from atar_core.display_v2 import get_theme
        t = get_theme("atar")
        assert t["primary"] == "#4FC3F7"

    def test_unknown_theme_fallback(self) -> None:
        from atar_core.display_v2 import get_theme
        t = get_theme("nonexistent")
        assert t["primary"] == "#4FC3F7"


class TestCost:
    def test_calculate_cost(self) -> None:
        from atar_core.display_v2 import calculate_cost
        cost = calculate_cost("deepseek-chat", 1000000, 1000000)
        assert cost > 0
