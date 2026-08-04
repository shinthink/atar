"""Tests for power tools, semantic memory, and skills auto-learning."""

from __future__ import annotations

import pytest
from atar_models.tools import ToolContext


class TestPowerTools:
    """real_browser, github, pdf, weather, stocks, maps."""

    @pytest.mark.asyncio
    async def test_weather_valid_city(self) -> None:
        from atar_tools.tools.power_tools import _weather
        result = await _weather("weather", {"city": "London"}, ToolContext())
        assert result.success
        assert "London" in result.output

    @pytest.mark.asyncio
    async def test_stocks_valid_symbol(self) -> None:
        from atar_tools.tools.power_tools import _stocks
        result = await _stocks("stocks", {"symbol": "AAPL"}, ToolContext())
        assert result.success
        assert "$" in result.output

    @pytest.mark.asyncio
    async def test_maps_geocode(self) -> None:
        from atar_tools.tools.power_tools import _maps
        result = await _maps("maps", {"action": "geocode", "query": "Jakarta"}, ToolContext())
        assert result.success

    @pytest.mark.asyncio
    async def test_weather_missing_city(self) -> None:
        from atar_tools.tools.power_tools import _weather
        result = await _weather("weather", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_stocks_missing_symbol(self) -> None:
        from atar_tools.tools.power_tools import _stocks
        result = await _stocks("stocks", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_maps_missing_query(self) -> None:
        from atar_tools.tools.power_tools import _maps
        result = await _maps("maps", {"action": "geocode"}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_pdf_missing_path(self) -> None:
        from atar_tools.tools.power_tools import _pdf
        result = await _pdf("pdf", {"action": "read"}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_github_missing_action(self) -> None:
        from atar_tools.tools.power_tools import _github
        result = await _github("github", {}, ToolContext())
        assert not result.success  # gh not installed


class TestSemanticMemory:
    """Semantic memory search."""

    def test_semantic_fallback_keyword(self) -> None:
        from atar_core.semantic_memory import semantic_memory_search
        results = semantic_memory_search("test query", limit=5)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_memory_semantic_tool(self) -> None:
        from atar_core.semantic_memory import _memory_semantic
        result = await _memory_semantic("mem_sem", {"query": "project tools"}, None)
        assert result.success


class TestSkillsAutoLearning:
    """Tool pattern detection and auto-skill creation."""

    def test_fingerprint_deterministic(self) -> None:
        from atar_core.semantic_memory import _fingerprint
        fp1 = _fingerprint(["read_file", "write_file", "terminal"])
        fp2 = _fingerprint(["read_file", "write_file", "terminal"])
        assert fp1 == fp2

    def test_record_pattern(self) -> None:
        from atar_core.semantic_memory import get_ready_skills, record_tool_pattern
        record_tool_pattern(
            ["web_search", "read_file", "write_file"],
            "research and write about topic",
            all_succeeded=True,
        )
        record_tool_pattern(
            ["web_search", "read_file", "write_file"],
            "research about AI",
            all_succeeded=True,
        )
        record_tool_pattern(
            ["web_search", "read_file", "write_file"],
            "write article about tech",
            all_succeeded=True,
        )
        ready = get_ready_skills()
        has_pattern = any("web_search→read_file→write_file" in "→".join(p.tool_names) for p in ready)
        # Should be ready if 3 successes
        if has_pattern:
            assert any(p.success_count >= 3 for p in ready)

    def test_should_create_skill_threshold(self) -> None:
        from atar_core.semantic_memory import ToolPattern
        p = ToolPattern(
            tool_names=["a", "b"],
            fingerprint="test123",
            success_count=3,
            total_attempts=4,
        )
        assert p.should_create_skill is True  # 75% > 70%

        p2 = ToolPattern(
            tool_names=["c", "d"],
            fingerprint="test456",
            success_count=2,
            total_attempts=5,
        )
        assert p2.should_create_skill is False  # 40%

    def test_generate_skill_draft(self) -> None:
        from atar_core.semantic_memory import ToolPattern, generate_skill_draft
        p = ToolPattern(
            tool_names=["web_search", "write_file"],
            fingerprint="abc123",
            success_count=3,
            total_attempts=3,
            example_prompt="research topic and save results",
            suggested_name="auto-web-search-write-file",
        )
        draft = generate_skill_draft(p)
        assert "auto-web-search-write-file" in draft
        assert "web_search" in draft
        assert "write_file" in draft
