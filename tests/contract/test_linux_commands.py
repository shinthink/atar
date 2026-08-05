"""Tests for Linux command dictionary."""

from __future__ import annotations


class TestLinuxCommands:
    """Linux command dictionary lookups."""

    def test_search_finds_ls(self) -> None:
        from atar_core.linux_commands import search_commands
        results = search_commands("ls")
        assert len(results) >= 1
        names = [r[0] for r in results]
        assert "ls" in names

    def test_search_by_description(self) -> None:
        from atar_core.linux_commands import search_commands
        results = search_commands("compress")
        assert len(results) >= 1
        names = [r[0] for r in results]
        assert "gzip" in names or "tar" in names

    def test_get_command_help(self) -> None:
        from atar_core.linux_commands import get_command_help
        info = get_command_help("ls")
        assert info is not None
        assert "description" in info
        assert info["category"] == "file"

    def test_get_command_help_unknown(self) -> None:
        from atar_core.linux_commands import get_command_help
        info = get_command_help("nonexistent_cmd")
        assert info is None

    def test_categories_exist(self) -> None:
        from atar_core.linux_commands import CATEGORIES
        assert "file" in CATEGORIES
        assert "text" in CATEGORIES
        assert "network" in CATEGORIES
        assert len(CATEGORIES) >= 15

    def test_get_by_category(self) -> None:
        from atar_core.linux_commands import get_commands_by_category
        results = get_commands_by_category("text")
        assert len(results) >= 10
        names = [r[0] for r in results]
        assert "grep" in names
        assert "cat" in names

    def test_all_commands_have_description(self) -> None:
        from atar_core.linux_commands import LINUX_COMMAND_DICT
        for name, info in LINUX_COMMAND_DICT.items():
            assert "description" in info, f"{name} missing description"
            assert "category" in info, f"{name} missing category"
            assert "examples" in info, f"{name} missing examples"

    def test_dangerous_commands(self) -> None:
        from atar_core.linux_commands import get_dangerous_commands
        dangerous = get_dangerous_commands()
        names = [d[0] for d in dangerous]
        assert "rm" in names
        assert "dd" in names
        assert "shutdown" in names

    def test_safe_commands(self) -> None:
        from atar_core.linux_commands import get_safe_commands
        safe = get_safe_commands()
        assert "ls" in safe
        assert "cat" in safe
        assert "echo" in safe
        # Dangerous commands NOT in safe list
        assert "rm" not in safe
        assert "dd" not in safe

    def test_command_count(self) -> None:
        from atar_core.linux_commands import LINUX_COMMAND_DICT
        assert len(LINUX_COMMAND_DICT) >= 100
