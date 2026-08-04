"""Tests for repl_display — pure display functions extracted from rich_repl.py."""

from __future__ import annotations


class TestToolIcons:
    """Tool icon mapping."""

    def test_all_known_tools_have_icon(self) -> None:
        from atar_cli.repl_display import TOOL_ICONS, tool_display_icon
        for name in TOOL_ICONS:
            icon = tool_display_icon(name)
            assert len(icon) >= 1

    def test_unknown_tool_icon(self) -> None:
        from atar_cli.repl_display import tool_display_icon
        icon = tool_display_icon("nonexistent_tool")
        assert icon == "\U0001f527"

    def test_read_write_icons(self) -> None:
        from atar_cli.repl_display import tool_display_icon
        assert "📖" in tool_display_icon("read_file") or "\U0001f4d6" in tool_display_icon("read_file")
        assert "✍" in tool_display_icon("write_file") or "\u270d" in tool_display_icon("write_file")


class TestToolPreview:
    """Tool display preview formatting."""

    def test_file_preview(self) -> None:
        from atar_cli.repl_display import tool_display_preview
        preview = tool_display_preview("write_file", {"path": "/tmp/test.txt", "content": "hello"})
        assert "/tmp/test.txt" in preview

    def test_terminal_preview(self) -> None:
        from atar_cli.repl_display import tool_display_preview
        preview = tool_display_preview("terminal", {"command": "ls -la /tmp"})
        assert "$ ls -la" in preview

    def test_generic_preview(self) -> None:
        from atar_cli.repl_display import tool_display_preview
        preview = tool_display_preview("web_search", {"query": "python testing"})
        assert "python" in preview


class TestBanner:
    """ASCII banner constants."""

    def test_cosmike_banner_lines(self) -> None:
        from atar_cli.repl_display import COSMIKE_BANNER
        assert len(COSMIKE_BANNER) == 6
        for line in COSMIKE_BANNER:
            assert any(x in line for x in [":::", ";;", "[[", "$$$", "888", "MMM"])

    def test_brain_logo_lines(self) -> None:
        from atar_cli.repl_display import BRAIN_LOGO
        assert len(BRAIN_LOGO) == 20
        assert all(len(line) == 42 for line in BRAIN_LOGO)

    def test_banner_colors(self) -> None:
        from atar_cli.repl_display import BANNER_COLORS
        assert len(BANNER_COLORS) == 6
        assert "primary" in BANNER_COLORS
        assert "accent" in BANNER_COLORS

    def test_tagline(self) -> None:
        from atar_cli.repl_display import TAGLINE
        assert "Clarity" in TAGLINE
        assert "Complexity" in TAGLINE


class TestFallbackResponse:
    """Response text fallback logic."""

    def test_has_text(self) -> None:
        from atar_cli.repl_display import fallback_response_text
        result = fallback_response_text("hello world", False)
        assert result == "hello world"

    def test_empty_with_tools(self) -> None:
        from atar_cli.repl_display import fallback_response_text
        result = fallback_response_text("", True)
        assert result is not None
        assert "Work completed" in result

    def test_empty_no_tools(self) -> None:
        from atar_cli.repl_display import fallback_response_text
        result = fallback_response_text("", False)
        assert result is None

    def test_whitespace_only(self) -> None:
        from atar_cli.repl_display import fallback_response_text
        result = fallback_response_text("   \n  ", True)
        assert "Work completed" in (result or "")


class TestToolResultLines:
    """Tool result display line formatting."""

    def test_terminal_result(self) -> None:
        from atar_cli.repl_display import format_tool_result_line
        lines = format_tool_result_line(
            "terminal", {"command": "echo hello"},
            "hello\nworld\ntest", 1.5,
        )
        assert len(lines) >= 1
        assert "terminal" in lines[-1]
        assert "1.5s" in lines[-1]

    def test_terminal_result_many_lines(self) -> None:
        from atar_cli.repl_display import format_tool_result_line
        many = "\n".join(f"line {i}" for i in range(20))
        lines = format_tool_result_line("terminal", {"command": "test"}, many, 0.5, max_lines=5)
        assert "more lines" in " ".join(lines)

    def test_write_result(self) -> None:
        from atar_cli.repl_display import format_tool_result_line
        lines = format_tool_result_line("write_file", {"path": "/tmp/x.txt"}, "content", 0.3)
        assert "write" in lines[0]
        assert "/tmp/x.txt" in lines[0]

    def test_read_result(self) -> None:
        from atar_cli.repl_display import format_tool_result_line
        lines = format_tool_result_line("read_file", {"path": "/tmp/y.txt"}, "abcde", 0.1)
        assert "read" in lines[0]
        assert "5 chars" in lines[0]

    def test_patch_result(self) -> None:
        from atar_cli.repl_display import format_tool_result_line
        lines = format_tool_result_line("patch", {"path": "/tmp/z.py"}, "diff", 0.2)
        assert "patch" in lines[0]

    def test_generic_result(self) -> None:
        from atar_cli.repl_display import format_tool_result_line
        lines = format_tool_result_line("web_search", {"query": "test"}, "results", 2.0)
        assert "web_search" in lines[0]
        assert "2.0s" in lines[0]
