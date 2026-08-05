"""Coverage tests for patch_tool, delegation, session tools, git, toolsets."""

from __future__ import annotations

import os

import pytest
from atar_models.tools import ToolContext

WORKSPACE = "/tmp/atar-cov-test"
os.makedirs(WORKSPACE, exist_ok=True)


class TestPatchTool:
    """patch_tool tests."""

    @pytest.mark.asyncio
    async def test_patch_creates_new_file(self) -> None:
        from atar_tools.tools.patch_tool import _patch_file

        path = os.path.join(WORKSPACE, "new_file.txt")
        if os.path.exists(path):
            os.unlink(path)
        old_cwd = os.getcwd()
        os.chdir(WORKSPACE)
        try:
            ctx = ToolContext(metadata={"workspace": WORKSPACE}, working_directory=WORKSPACE)
            result = await _patch_file("patch", {"path": "new_file.txt", "old_string": "x", "new_string": "hello world"}, ctx)
            assert result.success
            assert "Created" in result.output
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_patch_replace_in_file(self) -> None:
        from atar_tools.tools.patch_tool import _patch_file

        path = os.path.join(WORKSPACE, "patch_test.txt")
        with open(path, "w") as f:
            f.write("line one\nline two\nline three\n")
        old_cwd = os.getcwd()
        os.chdir(WORKSPACE)
        try:
            ctx = ToolContext(metadata={"workspace": WORKSPACE}, working_directory=WORKSPACE)
            result = await _patch_file("patch", {"path": "patch_test.txt", "old_string": "line two", "new_string": "LINE TWO"}, ctx)
            assert result.success
            with open(path) as f:
                content = f.read()
            assert "LINE TWO" in content
        finally:
            os.chdir(old_cwd)
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_patch_not_found(self) -> None:
        from atar_tools.tools.patch_tool import _patch_file

        path = os.path.join(WORKSPACE, "patch_test2.txt")
        with open(path, "w") as f:
            f.write("hello")
        old_cwd = os.getcwd()
        os.chdir(WORKSPACE)
        try:
            ctx = ToolContext(metadata={"workspace": WORKSPACE}, working_directory=WORKSPACE)
            result = await _patch_file("patch", {"path": "patch_test2.txt", "old_string": "notfound", "new_string": "x"}, ctx)
            assert not result.success
            assert "not found" in result.error.lower()
        finally:
            os.chdir(old_cwd)
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_patch_replace_all(self) -> None:
        from atar_tools.tools.patch_tool import _patch_file

        path = os.path.join(WORKSPACE, "patch_all.txt")
        with open(path, "w") as f:
            f.write("aaa 111 aaa 222 aaa\n")
        old_cwd = os.getcwd()
        os.chdir(WORKSPACE)
        try:
            ctx = ToolContext(metadata={"workspace": WORKSPACE}, working_directory=WORKSPACE)
            result = await _patch_file("patch", {"path": "patch_all.txt", "old_string": "aaa", "new_string": "BBB", "replace_all": True}, ctx)
            assert result.success
            with open(path) as f:
                content = f.read()
            assert content.count("BBB") == 3
        finally:
            os.chdir(old_cwd)
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_patch_missing_args(self) -> None:
        from atar_tools.tools.patch_tool import _patch_file

        ctx = ToolContext(metadata={"workspace": WORKSPACE})
        result = await _patch_file("patch", {}, ctx)
        assert not result.success


class TestDelegation:
    """delegate_task tests."""

    @pytest.mark.asyncio
    async def test_delegate_missing_goal(self) -> None:
        from atar_tools.tools.delegation import _delegate_task

        ctx = ToolContext(metadata={})
        result = await _delegate_task("delegate_task", {}, ctx)
        assert not result.success
        assert "goal required" in result.error.lower()


class TestSessionTools:
    """session_search and session_resume tests."""

    @pytest.mark.asyncio
    async def test_session_search_no_query(self) -> None:
        from atar_tools.tools.session import _session_search

        ctx = ToolContext(metadata={})
        result = await _session_search("session_search", {"query": ""}, ctx)
        # Empty query lists all sessions — should succeed
        assert result.success

    @pytest.mark.asyncio
    async def test_session_resume_missing_id(self) -> None:
        from atar_tools.tools.session import _session_resume

        ctx = ToolContext(metadata={})
        result = await _session_resume("session_resume", {}, ctx)
        assert not result.success


class TestGitTools:
    """git tool tests."""

    @pytest.mark.asyncio
    async def test_git_no_args(self) -> None:
        from atar_tools.tools.git import _git

        ctx = ToolContext(metadata={})
        result = await _git("git", {}, ctx)
        assert result.success  # git works with sandbox:False

    @pytest.mark.asyncio
    async def test_git_help(self) -> None:
        from atar_tools.tools.git import _git

        # Test unknown git op
        ctx = ToolContext(metadata={"approved": True})
        result = await _git("git", {"op": "unknown_op"}, ctx)
        assert not result.success
        assert "unknown" in result.error.lower()


class TestToolsets:
    """Toolsets module tests."""

    def test_get_toolsets(self) -> None:
        from atar_tools.toolsets import get_toolsets

        toolsets = get_toolsets()
        assert len(toolsets) > 0
        assert "file" in toolsets

    def test_enabled_toolsets(self) -> None:
        from atar_tools.toolsets import enabled_toolsets

        names = enabled_toolsets()
        assert "file" in names
        assert "terminal" in names

    def test_tools_for_toolsets(self) -> None:
        from atar_tools.toolsets import tools_for_toolsets

        tools = tools_for_toolsets(["file"])
        names = [t.name for t in tools]
        assert "read_file" in names or "write_file" in names

    def test_set_active_toolset(self) -> None:
        from atar_tools.toolsets import get_active_toolset, set_active_toolset

        set_active_toolset("web")
        assert get_active_toolset() == "web"
        set_active_toolset("")

    def test_get_active_toolset_names(self) -> None:
        from atar_tools.toolsets import get_active_toolset_names, set_active_toolset

        set_active_toolset("terminal")
        names = get_active_toolset_names()
        assert "terminal" in names
        set_active_toolset("")


class TestTerminalMore:
    """Additional terminal coverage."""

    @pytest.mark.asyncio
    async def test_terminal_missing_command(self) -> None:
        from atar_tools.tools.terminal import _run_terminal

        ctx = ToolContext(metadata={})
        result = await _run_terminal("terminal", {}, ctx)
        assert not result.success
        assert "command required" in result.error.lower()

    @pytest.mark.asyncio
    async def test_terminal_command_not_found(self) -> None:
        from atar_tools.tools.terminal import _run_terminal

        ctx = ToolContext(metadata={})
        result = await _run_terminal("terminal", {"command": "nonexistent_cmd_xyz"}, ctx)
        assert not result.success


class TestRegistryCoverage:
    """Tool registry edge cases."""

    def test_get_nonexistent_tool(self) -> None:
        from atar_tools.registry import get

        assert get("nonexistent_tool_xyz") is None

    def test_list_toolset_nonexistent(self) -> None:
        from atar_tools.registry import list_toolset

        assert list_toolset("nonexistent") == []

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self) -> None:
        from atar_tools.registry import execute

        result = await execute("nonexistent", {}, ToolContext())
        assert not result.success

    @pytest.mark.asyncio
    async def test_execute_requires_approval(self) -> None:
        from atar_tools.registry import execute, list_all

        # Find a tool that requires approval
        approved_tools = [t for t in list_all() if t.requires_approval]
        if approved_tools:
            tool = approved_tools[0]
            result = await execute(tool.name, {}, ToolContext())
            assert not result.success
            assert "requires approval" in result.error.lower()

    def test_to_openai_schema(self) -> None:
        from atar_tools.registry import list_all, to_openai_schema

        tools = list_all()
        if tools:
            schema = to_openai_schema(tools[0])
            assert schema["type"] == "function"
            assert "function" in schema

    def test_to_anthropic_schema(self) -> None:
        from atar_tools.registry import list_all, to_anthropic_schema

        tools = list_all()
        if tools:
            schema = to_anthropic_schema(tools[0])
            assert "name" in schema
            assert "input_schema" in schema


class TestSecretsCoverage:
    """Secrets module edge cases."""

    def test_delete_api_key(self) -> None:
        from atar_security.secrets import delete_api_key

        # Should not crash even if no key exists
        result = delete_api_key("nonexistent_provider")
        assert result is True

    def test_is_first_run_no_config(self) -> None:
        from atar_security.secrets import is_first_run

        # Should not crash
        result = is_first_run()
        assert isinstance(result, bool)
