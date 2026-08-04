"""Tests for rich_repl_helpers — pure functions extracted from rich_repl.py."""

from __future__ import annotations

import os
import time


class TestToolRisk:
    """Tool classification by risk level."""

    def test_read_only_tools(self) -> None:
        from atar_cli.rich_repl_helpers import tool_risk
        for name in ["read_file", "search_files", "session_search", "session_resume", "git"]:
            risk, color = tool_risk(name)
            assert risk == "Read-only"
            assert color == "#4ADE80"

    def test_network_tools(self) -> None:
        from atar_cli.rich_repl_helpers import tool_risk
        for name in ["web_search", "web_fetch", "browser"]:
            risk, color = tool_risk(name)
            assert risk == "Network"
            assert color == "#FBBF24"

    def test_write_tools(self) -> None:
        from atar_cli.rich_repl_helpers import tool_risk
        for name in ["write_file", "patch"]:
            risk, color = tool_risk(name)
            assert risk == "Write"
            assert color == "#F87171"

    def test_execute_tools(self) -> None:
        from atar_cli.rich_repl_helpers import tool_risk
        for name in ["terminal", "run_tests", "execute_code", "cronjob", "delegate_task"]:
            risk, color = tool_risk(name)
            assert risk == "Execute"
            assert color == "#EF4444"

    def test_unknown_tool(self) -> None:
        from atar_cli.rich_repl_helpers import tool_risk
        risk, color = tool_risk("nonexistent_tool_xyz")
        assert risk == "Unknown"
        assert color == "#9CA3AF"


class TestBasePrompt:
    """System prompt template."""

    def test_base_prompt_contains_keywords(self) -> None:
        from atar_cli.rich_repl_helpers import BASE_PROMPT
        assert "ATAR" in BASE_PROMPT
        assert "web_search" in BASE_PROMPT
        assert "write_file" in BASE_PROMPT
        assert "Linux" in BASE_PROMPT
        assert "concise" in BASE_PROMPT

    def test_base_prompt_no_name_fabrication(self) -> None:
        from atar_cli.rich_repl_helpers import BASE_PROMPT
        assert "fabricate" in BASE_PROMPT
        assert "assume" in BASE_PROMPT

    def test_base_prompt_action_directives(self) -> None:
        from atar_cli.rich_repl_helpers import BASE_PROMPT
        assert "IMMEDIATELY" in BASE_PROMPT
        assert "I will" in BASE_PROMPT
        assert "Saya akan" in BASE_PROMPT


class TestConfigHelpers:
    """Config read/write operations."""

    def test_read_config_missing_file(self) -> None:
        from atar_cli.rich_repl_helpers import _read_config
        # Should not crash when config doesn't exist
        cfg = _read_config()
        assert isinstance(cfg, dict)

    def test_save_and_read_config(self) -> None:
        from atar_cli.rich_repl_helpers import _read_config, _save_config
        config_path = os.path.expanduser("~/.atar/config.json")
        backup = None
        if os.path.exists(config_path):
            with open(config_path) as f:
                backup = f.read()
        try:
            _save_config({"test_key": "test_value", "model": "test-model"})
            cfg = _read_config()
            assert cfg["test_key"] == "test_value"
            assert cfg["model"] == "test-model"
        finally:
            if backup is not None:
                with open(config_path, "w") as f:
                    f.write(backup)

    def test_switch_model_config(self) -> None:
        from atar_cli.rich_repl_helpers import _read_config, switch_model_config
        config_path = os.path.expanduser("~/.atar/config.json")
        backup = None
        if os.path.exists(config_path):
            with open(config_path) as f:
                backup = f.read()
        try:
            display = switch_model_config("deepseek", "deepseek-v4-pro")
            assert "DeepSeek" in display
            assert "deepseek-v4-pro" in display
            cfg = _read_config()
            assert cfg["provider"] == "deepseek"
            assert cfg["model"] == "deepseek-v4-pro"
        finally:
            if backup is not None:
                with open(config_path, "w") as f:
                    f.write(backup)


class TestCwdShorten:
    """Working directory display shortening."""

    def test_short_cwd_normal(self) -> None:
        from atar_cli.rich_repl_helpers import short_cwd
        result = short_cwd("/home/user/projects/myapp")
        assert len(result) <= 50

    def test_short_cwd_home_expansion(self) -> None:
        from atar_cli.rich_repl_helpers import short_cwd
        home = os.path.expanduser("~")
        result = short_cwd(home + "/projects/test")
        assert result.startswith("~")
        assert "projects/test" in result

    def test_short_cwd_long_path(self) -> None:
        from atar_cli.rich_repl_helpers import short_cwd
        long_path = "/" + "very_long_directory_name/" * 10
        result = short_cwd(long_path)
        assert len(result) <= 50
        assert result.startswith("...")


class TestContextBar:
    """Context bar computation."""

    def test_empty_context(self) -> None:
        from atar_cli.rich_repl_helpers import compute_context_bar
        result = compute_context_bar(0, 128000)
        assert "0.0K" in result
        assert "0%" in result

    def test_half_full(self) -> None:
        from atar_cli.rich_repl_helpers import compute_context_bar
        result = compute_context_bar(64000, 128000)
        assert "50%" in result

    def test_zero_max_tokens(self) -> None:
        from atar_cli.rich_repl_helpers import compute_context_bar
        result = compute_context_bar(5000, 0)
        assert "128K" in result  # falls back to 128000

    def test_full_context(self) -> None:
        from atar_cli.rich_repl_helpers import compute_context_bar
        result = compute_context_bar(200000, 128000)
        assert "100%" in result


class TestStatusBar:
    """Status bar assembly."""

    def test_basic_status_bar(self) -> None:
        from atar_cli.rich_repl_helpers import compute_status_bar
        bar = compute_status_bar(
            model="deepseek-v4-pro", turns=5, tools=12, tokens=10000, tokens_out=5000,
            cost=0.05, start_time=time.time() - 120, term_width=80,
        )
        assert "deepseek-v4-pro" in bar
        assert "turns 5" in bar
        assert "tools 12" in bar
        assert "$0.05" in bar

    def test_narrow_status_bar(self) -> None:
        from atar_cli.rich_repl_helpers import compute_status_bar
        bar = compute_status_bar(
            model="test-model", turns=1, tools=0, tokens=0, tokens_out=0,
            start_time=time.time() - 60, term_width=50,
        )
        assert "turns" not in bar  # narrow mode omits turns/tools

    def test_very_narrow_status_bar(self) -> None:
        from atar_cli.rich_repl_helpers import compute_status_bar
        bar = compute_status_bar(
            model="x", turns=0, tools=0, tokens=0, tokens_out=0,
            start_time=time.time() - 5, term_width=30,
        )
        assert "x" in bar

    def test_status_bar_with_compressions(self) -> None:
        from atar_cli.rich_repl_helpers import compute_status_bar
        bar = compute_status_bar(
            model="test", compressions=3, term_width=80,
        )
        assert "3" in bar  # compression count included

    def test_no_start_time_defaults(self) -> None:
        from atar_cli.rich_repl_helpers import compute_status_bar
        bar = compute_status_bar(start_time=None, term_width=80)
        assert isinstance(bar, str)
        assert len(bar) > 0


class TestReplStats:
    """ReplStats container."""

    def test_default_values(self) -> None:
        from atar_cli.rich_repl_helpers import ReplStats
        stats = ReplStats()
        assert stats.turns == 0
        assert stats.tools == 0
        assert stats.model == "deepseek-chat"
        assert stats.start_time is None

    def test_mutation(self) -> None:
        from atar_cli.rich_repl_helpers import ReplStats
        stats = ReplStats()
        stats.turns = 10
        stats.tools = 25
        stats.tokens = 5000
        stats.cost = 0.25
        assert stats.turns == 10
        assert stats.cost == 0.25

    def test_to_dict(self) -> None:
        from atar_cli.rich_repl_helpers import ReplStats
        stats = ReplStats()
        stats.turns = 3
        stats.model = "claude-sonnet-4"
        d = stats.to_dict()
        assert d["turns"] == 3
        assert d["model"] == "claude-sonnet-4"
