"""UI-1: Display engine tests."""

from __future__ import annotations

from atar_core.display import (
    TOOL_ICONS,
    ThinkingAnimator,
    calculate_cost,
    context_bar,
    cycle_verbose,
    get_verbose,
)


class TestContextBar:
    def test_green_below_50(self):
        bar, color = context_bar(10000, 128000)
        assert "4ADE80" in color

    def test_yellow_range(self):
        bar, color = context_bar(80000, 128000)
        assert "FBBF24" in color

    def test_red_above_95(self):
        bar, color = context_bar(125000, 128000)
        assert "F87171" in color

    def test_empty(self):
        bar, color = context_bar(0, 128000)
        assert "0.0K" in bar or "0K" in bar

    def test_orange_range(self):
        bar, color = context_bar(115000, 128000)
        assert "FB923C" in color


class TestPricing:
    def test_cost_known(self):
        cost = calculate_cost("deepseek-v4-pro", 1000000, 500000)
        assert cost > 0

    def test_cost_zero_for_unknown(self):
        cost = calculate_cost("", 0, 0)
        assert cost == 0.0

class TestThinkingAnimator:
    def test_start_returns_string(self):
        anim = ThinkingAnimator()
        result = anim.start()
        assert "thinking" in result.lower() or "processing" in result.lower()

    def test_tick_cycles(self):
        anim = ThinkingAnimator()
        first = anim.start()
        second = anim.tick()
        assert second != first  # frame should change

    def test_static_line(self):
        static = ThinkingAnimator.static_line()
        assert "thinking" in static.lower()


class TestVerbose:
    def test_cycle_wraps(self):
        before = get_verbose()
        for _ in range(4):
            cycle_verbose()
        assert get_verbose() == before

    def test_cycle_returns_name(self):
        name = cycle_verbose()
        assert name in ("new", "all", "verbose", "off")


class TestToolIcons:
    def test_all_12_tools_have_icons(self):
        tools = ["read_file", "write_file", "terminal", "web_search", "web_fetch",
                 "git", "run_tests", "patch", "search_files", "browser",
                 "execute_code", "delegate_task", "cronjob"]
        for t in tools:
            assert t in TOOL_ICONS, f"Missing icon for {t}"
            assert TOOL_ICONS[t], f"Empty icon for {t}"
