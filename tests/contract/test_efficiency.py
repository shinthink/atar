"""Tests for efficiency engine: compression, parallel, caching, workspace detection."""

from __future__ import annotations


class TestSmartCompression:
    """Smart context compression."""

    def test_estimate_tokens(self) -> None:
        from atar_core.efficiency import estimate_tokens
        assert estimate_tokens("hello") == 1  # 5 chars // 4 = 1
        assert estimate_tokens("a" * 100) == 25  # 100 // 4 = 25

    def test_short_history_not_compressed(self) -> None:
        from atar_core.efficiency import compress_history
        short = [{"role": "system", "content": "hi"}]
        result = compress_history(short)
        assert len(result) == 1

    def test_long_history_compressed(self) -> None:
        from atar_core.efficiency import compress_history
        # Create a long history
        messages = [{"role": "system", "content": "You are an AI"}]
        for i in range(15):
            messages.append({"role": "user", "content": f"Message {i} " + "x" * 300})
            messages.append({"role": "assistant", "content": f"Response {i} " + "y" * 300})
        result = compress_history(messages)
        assert len(result) <= len(messages)
        # First message preserved
        assert result[0]["role"] == "system"


class TestParallelExecution:
    """Parallel tool execution."""

    def test_can_parallelize_reads(self) -> None:
        from atar_core.efficiency import can_parallelize
        assert can_parallelize(["read_file", "web_search", "weather"]) is True

    def test_cannot_parallelize_writes(self) -> None:
        from atar_core.efficiency import can_parallelize
        assert can_parallelize(["write_file", "read_file"]) is False


class TestToolCaching:
    """Tool result caching."""

    def test_cache_hit(self) -> None:
        from atar_core.efficiency import cache_result, cached_execute, clear_cache
        clear_cache()
        result, hit = cached_execute("read_file", {"path": "/tmp/test.txt"})
        assert hit is False

        cache_result("read_file", {"path": "/tmp/test.txt"}, "cached content")
        result, hit = cached_execute("read_file", {"path": "/tmp/test.txt"})
        assert hit is True
        assert result == "cached content"

    def test_cache_key_ordering(self) -> None:
        from atar_core.efficiency import _cache_key
        k1 = _cache_key("read_file", {"path": "a", "offset": 1})
        k2 = _cache_key("read_file", {"offset": 1, "path": "a"})
        assert k1 == k2

    def test_on_write_clears_cache(self) -> None:
        from atar_core.efficiency import cache_result, cached_execute, clear_cache, on_write_operation
        clear_cache()
        cache_result("read_file", {"path": "x"}, "data")
        on_write_operation("write_file")
        _, hit = cached_execute("read_file", {"path": "x"})
        assert hit is False  # Cache should be cleared after write


class TestWorkspaceDetection:
    """Workspace auto-detection."""

    def test_detect_current_workspace(self) -> None:
        from atar_core.efficiency import detect_workspace
        info = detect_workspace(".")
        assert info.language == "Python"
        assert "pyproject.toml" in info.config_files
        assert info.git_initialized is True
        assert info.total_files > 0

    def test_get_workspace_context(self) -> None:
        from atar_core.efficiency import get_workspace_context
        ctx = get_workspace_context(".")
        assert "Python" in ctx
        assert "pytest" in ctx.lower()
