"""Priority 1: Diff preview & granular approval tests."""

from __future__ import annotations

from atar_tools.tools.diff_renderer import render_diff, diff_stats_line
from atar_core.approval import ApprovalState, get_approval, reset_approval


class TestDiffRenderer:
    def test_simple_change(self):
        markup, plain, stats = render_diff("hello", "world", "test.txt")
        assert "+world" in plain
        assert "-hello" in plain
        assert stats["added"] >= 1

    def test_no_change(self):
        markup, plain, stats = render_diff("same", "same", "test.txt")
        assert stats["total_lines"] == 0

    def test_added_lines_count(self):
        _, _, stats = render_diff("", "line1\nline2\nline3", "test.txt")
        assert stats["added"] == 3

    def test_stats_line(self):
        line = diff_stats_line({"added": 12, "removed": 4})
        assert "+12" in line
        assert "-4" in line


class TestApprovalFlow:
    def setup_method(self):
        reset_approval()

    def test_default_ask(self):
        a = get_approval()
        assert a.resolve("write_file") == "ask"

    def test_yolo_bypasses(self):
        a = get_approval()
        a.yolo = True
        assert a.resolve("terminal") == "approve"

    def test_file_always(self):
        a = get_approval()
        a.add_file_always("/tmp/test.py")
        assert a.resolve("write_file", "/tmp/test.py") == "approve"
        assert a.resolve("write_file", "/tmp/other.py") == "ask"

    def test_tool_always(self):
        a = get_approval()
        a.set_tool_mode("patch", "always")
        assert a.resolve("patch") == "approve"

    def test_tool_never(self):
        a = get_approval()
        a.set_tool_mode("terminal", "never")
        assert a.resolve("terminal") == "reject"

    def test_reset_clears(self):
        a = get_approval()
        a.yolo = True
        a.set_tool_mode("write_file", "always")
        reset_approval()
        a2 = get_approval()
        assert a2.yolo is False
        assert a2.resolve("write_file") == "ask"
