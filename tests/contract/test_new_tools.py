"""Tests for new tools: search_files, browser, execute_code, cronjob, memory_add, memory_list."""

from __future__ import annotations

import os

import pytest
from atar_models.tools import ToolContext


class TestSearchFiles:
    """search_files tool."""

    @pytest.mark.asyncio
    async def test_search_missing_pattern(self) -> None:
        from atar_tools.tools.missing_tools import _search_files
        result = await _search_files("search_files", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_search_files_by_glob(self) -> None:
        from atar_tools.tools.missing_tools import _search_files
        ctx = ToolContext(working_directory=os.getcwd())
        result = await _search_files("search_files", {"pattern": "*", "target": "files", "path": ".", "limit": 3}, ctx)
        assert result.success

    @pytest.mark.asyncio
    async def test_search_content(self) -> None:
        from atar_tools.tools.missing_tools import _search_files
        ctx = ToolContext(working_directory=os.getcwd())
        result = await _search_files("search_files", {"pattern": "def test_", "target": "content", "path": "tests/", "limit": 5}, ctx)
        assert result.success


class TestBrowser:
    """browser tool."""

    @pytest.mark.asyncio
    async def test_browser_missing_url(self) -> None:
        from atar_tools.tools.missing_tools import _browser
        result = await _browser("browser", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_browser_fetch(self) -> None:
        from atar_tools.tools.missing_tools import _browser
        result = await _browser("browser", {"url": "https://example.com"}, ToolContext())
        assert result.success
        assert "Example" in result.output


class TestExecuteCode:
    """execute_code tool."""

    @pytest.mark.asyncio
    async def test_execute_missing_code(self) -> None:
        from atar_tools.tools.missing_tools import _execute_code
        result = await _execute_code("execute_code", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_execute_simple(self) -> None:
        from atar_tools.tools.missing_tools import _execute_code
        result = await _execute_code("execute_code", {"code": "print('hello world')"}, ToolContext())
        assert result.success
        assert "hello world" in result.output

    @pytest.mark.asyncio
    async def test_execute_math(self) -> None:
        from atar_tools.tools.missing_tools import _execute_code
        result = await _execute_code("execute_code", {"code": "print(sum(range(100)))"}, ToolContext())
        assert result.success
        assert "4950" in result.output

    @pytest.mark.asyncio
    async def test_execute_error(self) -> None:
        from atar_tools.tools.missing_tools import _execute_code
        result = await _execute_code("execute_code", {"code": "1/0"}, ToolContext())
        assert not result.success


class TestCronjob:
    """cronjob tool."""

    @pytest.mark.asyncio
    async def test_cronjob_list(self) -> None:
        from atar_tools.tools.missing_tools import _cronjob
        result = await _cronjob("cronjob", {"action": "list"}, ToolContext())
        assert result.success

    @pytest.mark.asyncio
    async def test_cronjob_create_missing_prompt(self) -> None:
        from atar_tools.tools.missing_tools import _cronjob
        result = await _cronjob("cronjob", {"action": "create"}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_cronjob_unknown_action(self) -> None:
        from atar_tools.tools.missing_tools import _cronjob
        result = await _cronjob("cronjob", {"action": "unknown"}, ToolContext())
        assert not result.success


class TestMemoryTools:
    """memory_add and memory_list tools."""

    @pytest.mark.asyncio
    async def test_memory_add_missing_content(self) -> None:
        from atar_tools.tools.missing_tools import _memory_add
        result = await _memory_add("memory_add", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_memory_add_and_list(self) -> None:
        from atar_tools.tools.missing_tools import _memory_add, _memory_list
        result = await _memory_add("memory_add", {"content": "test memory entry for tool test", "category": "fact"}, ToolContext())
        assert result.success

        result2 = await _memory_list("memory_list", {"limit": 5}, ToolContext())
        assert result2.success
        assert "test memory entry" in result2.output

    @pytest.mark.asyncio
    async def test_memory_list_empty(self) -> None:
        from atar_tools.tools.missing_tools import _memory_list
        result = await _memory_list("memory_list", {"query": "nonexistent_xyz_12345"}, ToolContext())
        assert result.success


class TestToolRegistration:
    """Verify all new tools are registered."""

    def test_all_tools_registered(self) -> None:
        from atar_tools.registry import list_all
        tools = {t.name for t in list_all()}
        expected = {"search_files", "browser", "execute_code", "cronjob", "memory_add", "memory_list"}
        for name in expected:
            assert name in tools, f"Tool '{name}' not registered"
