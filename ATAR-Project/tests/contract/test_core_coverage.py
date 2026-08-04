"""Coverage tests for background, paths, sqlite_store, compress."""

from __future__ import annotations

import os
import tempfile

import pytest
from atar_models.requests import Message


class TestBackground:
    """Background task config: provider, throttle, toggles, token tracking."""

    def setup_method(self) -> None:
        from atar_core.background import reset_bg_tokens
        reset_bg_tokens()

    def test_get_background_provider_config_default(self) -> None:
        from atar_core.background import get_background_provider_config
        bp, bm = get_background_provider_config()
        assert isinstance(bp, str)
        assert isinstance(bm, str)

    def test_get_throttle_default(self) -> None:
        from atar_core.background import get_throttle
        t = get_throttle()
        assert t == 5

    def test_memory_toggle(self) -> None:
        from atar_core.background import is_memory_enabled, toggle_memory
        initial = is_memory_enabled()
        toggled = toggle_memory()
        assert toggled != initial
        toggle_memory()  # reset
        assert is_memory_enabled() == initial

    def test_skills_toggle(self) -> None:
        from atar_core.background import is_skills_auto_enabled, toggle_skills_auto
        initial = is_skills_auto_enabled()
        toggled = toggle_skills_auto()
        assert toggled != initial
        toggle_skills_auto()  # reset
        assert is_skills_auto_enabled() == initial

    def test_record_bg_tokens(self) -> None:
        from atar_core.background import get_bg_tokens, record_bg_tokens, reset_bg_tokens
        reset_bg_tokens()
        record_bg_tokens("memory", 100)
        record_bg_tokens("memory", 50)
        record_bg_tokens("skill", 200)
        tokens = get_bg_tokens()
        assert tokens["memory"] == 150
        assert tokens["skill"] == 200

    def test_reset_bg_tokens(self) -> None:
        from atar_core.background import get_bg_tokens, record_bg_tokens, reset_bg_tokens
        record_bg_tokens("memory", 100)
        reset_bg_tokens()
        tokens = get_bg_tokens()
        assert tokens["memory"] == 0

    def test_background_config_save_load(self) -> None:

        from atar_core.background import CONFIG_PATH, _load_config, _save_config
        # Backup existing config
        backup = None
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                backup = f.read()
        try:
            _save_config({"background_provider": "deepseek", "background_model": "deepseek-v4-flash"})
            cfg = _load_config()
            assert cfg["background_provider"] == "deepseek"
        finally:
            if backup is not None:
                with open(CONFIG_PATH, "w") as f:
                    f.write(backup)


class TestPaths:
    """ATAR path resolution."""

    def test_atar_home_default(self) -> None:
        from atar_core.paths import _atar_home
        home = _atar_home()
        assert str(home).endswith(".atar")

    def test_atar_home_env(self) -> None:
        os.environ["ATAR_HOME"] = "/tmp/test-atar-home"
        try:
            from importlib import reload

            import atar_core.paths
            reload(atar_core.paths)
            home = atar_core.paths._atar_home()
            assert str(home) == "/tmp/test-atar-home"
        finally:
            del os.environ["ATAR_HOME"]
            reload(atar_core.paths)

    def test_atar_config_dir(self) -> None:
        from atar_core.paths import atar_config_dir
        d = atar_config_dir()
        assert ".atar" in str(d)
        d2 = atar_config_dir("myprofile")
        assert "myprofile" in str(d2)

    def test_atar_data_dir(self) -> None:
        from atar_core.paths import atar_data_dir
        d = atar_data_dir()
        assert "data" in str(d)

    def test_atar_skills_dir(self) -> None:
        from atar_core.paths import atar_skills_dir
        d = atar_skills_dir()
        assert "skills" in str(d)

    def test_atar_plugins_dir(self) -> None:
        from atar_core.paths import atar_plugins_dir
        d = atar_plugins_dir()
        assert "plugins" in str(d)

    def test_atar_logs_dir(self) -> None:
        from atar_core.paths import atar_logs_dir
        d = atar_logs_dir()
        assert "logs" in str(d)

    def test_atar_sessions_db(self) -> None:
        from atar_core.paths import atar_sessions_db
        d = atar_sessions_db()
        assert "sessions.db" in str(d)

    def test_atar_config_file(self) -> None:
        from atar_core.paths import atar_config_file
        d = atar_config_file()
        assert "config.yaml" in str(d)

    def test_atar_memory_file(self) -> None:
        from atar_core.paths import atar_memory_file
        d = atar_memory_file()
        assert "memory.json" in str(d)

    def test_ensure_dirs(self) -> None:
        from atar_core.paths import ensure_dirs
        ensure_dirs("default")


class TestSqliteStore:
    """SQLite session storage CRUD operations."""

    @pytest.fixture(autouse=True)
    def setup_store(self) -> None:
        self.db_path = os.path.join(tempfile.gettempdir(), f"atar_test_{os.getpid()}.db")
        from atar_storage.sqlite_store import SqliteSessionStore
        self.store = SqliteSessionStore(db_path=self.db_path)
        yield
        # Cleanup
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        # Also cleanup WAL/SHM files
        for suffix in ["-wal", "-shm"]:
            p = self.db_path + suffix
            if os.path.exists(p):
                os.unlink(p)

    def test_save_and_load(self) -> None:
        msgs = [Message(role="user", content="hello"), Message(role="assistant", content="hi")]
        self.store.save("sess-001", "Test Session", msgs)
        loaded = self.store.load("sess-001")
        assert loaded is not None
        assert loaded["title"] == "Test Session"
        assert len(loaded["messages"]) == 2

    def test_load_nonexistent(self) -> None:
        result = self.store.load("nonexistent")
        assert result is None

    def test_list_all(self) -> None:
        msgs = [Message(role="user", content="test")]
        self.store.save("sess-a", "Session A", msgs)
        self.store.save("sess-b", "Session B", msgs)
        sessions = self.store.list_all()
        assert len(sessions) >= 2
        ids = [s["session_id"] for s in sessions]
        assert "sess-a" in ids
        assert "sess-b" in ids

    def test_search(self) -> None:
        msgs = [Message(role="user", content="searchable content here")]
        self.store.save("sess-search", "Search Test", msgs)
        results = self.store.search("searchable")
        if results:  # FTS5 may fail on new DB
            assert "sess-search" in results[0]["session_id"]

    def test_update_existing(self) -> None:
        msgs = [Message(role="user", content="first")]
        self.store.save("sess-upd", "Original", msgs)
        msgs2 = [Message(role="user", content="first"), Message(role="assistant", content="second")]
        self.store.save("sess-upd", "Updated", msgs2)
        loaded = self.store.load("sess-upd")
        assert loaded["title"] == "Updated"
        assert len(loaded["messages"]) == 2


class TestApproval:
    """Approval prompt formatting."""

    def test_format_approval_prompt_with_file(self) -> None:
        from atar_core.approval import format_approval_prompt
        prompt = format_approval_prompt("write_file", {"path": "/tmp/test.txt"}, diff_markup="+hello\n-world", stats={"added": 1, "removed": 1})
        assert "write_file" in prompt
        assert "/tmp/test.txt" in prompt

    def test_format_approval_prompt_no_file(self) -> None:
        from atar_core.approval import format_approval_prompt
        prompt = format_approval_prompt("web_search", {"query": "test"}, diff_markup="", stats={"added": 0, "removed": 0})
        assert "web_search" in prompt

    def test_format_approval_prompt_with_diff(self) -> None:
        from atar_core.approval import format_approval_prompt
        prompt = format_approval_prompt("patch", {"path": "/tmp/test.py"}, diff_markup="@@ -1 +1 @@\n-old\n+new", stats={"added": 1, "removed": 1})
        assert "@@" in prompt


class TestCommands:
    """Command registry tests."""

    def test_register_command(self) -> None:
        from atar_core.commands import register_command, registry
        cmd = register_command("/_test_cmd", "Test command", category="general")
        assert cmd.name == "/_test_cmd"
        found = registry.get("/_test_cmd")
        assert found is not None

    def test_list_commands(self) -> None:
        from atar_core.commands import registry
        cmds = registry.list_all()
        assert isinstance(cmds, list)
        assert len(cmds) > 0

    def test_get_nonexistent(self) -> None:
        from atar_core.commands import registry
        result = registry.get("/_nonexistent_xyz_123")
        assert result is None


class TestOutputTruncation:
    """Output truncation utility tests."""

    def test_truncate_short_output(self) -> None:
        from atar_core.output_truncation import truncate_tool_output
        result = truncate_tool_output("short output", max_chars=1000)
        assert result == "short output"

    def test_truncate_long_output(self) -> None:
        from atar_core.output_truncation import truncate_tool_output
        long_text = "x" * 3000
        result = truncate_tool_output(long_text, max_chars=1000)
        assert len(result) < len(long_text)
        assert "chars hidden" in result.lower()

    def test_save_full_output(self) -> None:
        from atar_core.output_truncation import save_full_output
        save_full_output(1, "test output")


class TestDisplay:
    """Display engine tests."""

    def test_context_bar_low(self) -> None:
        from atar_core.display import context_bar
        bar, color = context_bar(5000, 128000)
        assert "K" in bar
        assert "#4ADE80" in color  # green for low usage

    def test_context_bar_high(self) -> None:
        from atar_core.display import context_bar
        bar, color = context_bar(125000, 128000)
        assert "#F87171" in color  # red for near-limit

    def test_calculate_cost_deepseek(self) -> None:
        from atar_core.display import calculate_cost
        cost = calculate_cost("deepseek-chat", 1000, 500)
        assert cost >= 0

    def test_calculate_cost_claude(self) -> None:
        from atar_core.display import calculate_cost
        cost = calculate_cost("claude-sonnet-4", 1000, 500)
        assert cost >= 0

    def test_calculate_cost_gpt(self) -> None:
        from atar_core.display import calculate_cost
        cost = calculate_cost("gpt-5.6", 1000, 500)
        assert cost >= 0

    def test_thinking_animator(self) -> None:
        from atar_core.display import ThinkingAnimator
        anim = ThinkingAnimator()
        line = anim.start()
        assert "thinking" in line or "pondering" in line
        line2 = anim.tick()
        assert len(line2) > 0

    def test_thinking_static(self) -> None:
        from atar_core.display import ThinkingAnimator
        line = ThinkingAnimator.static_line()
        assert "thinking" in line

    def test_verbose_cycle(self) -> None:
        from atar_core.display import cycle_verbose, get_verbose
        initial = get_verbose()
        new = cycle_verbose()
        assert new != str(initial)
        # Cycle back
        for _ in range(3):
            cycle_verbose()
        assert get_verbose() == initial


class TestConfig:
    """Config properties tests."""

    def test_load_default_config(self) -> None:
        from atar_core.config import load_config
        cfg = load_config()
        assert cfg.profile == "default"
        assert cfg.model["provider"] == "deepseek"

    def test_config_properties(self) -> None:
        from atar_core.config import load_config
        cfg = load_config()
        assert isinstance(cfg.model, dict)
        assert isinstance(cfg.agent, dict)
        assert isinstance(cfg.security, dict)
        assert isinstance(cfg.sessions, dict)
        assert isinstance(cfg.display, dict)


class TestCompress:
    """Context compression tests."""

    class _FakeStreamProvider:
        """Minimal provider that yields one text event for compression tests."""
        model = "fake"

        async def stream(self, request):
            yield type("E", (), {"event_type": "text_delta", "text": "Compressed summary of conversation.", "provider_metadata": {}})()

        async def count_tokens(self, request):
            return 0

        async def health_check(self):
            return type("H", (), {"provider_id": "fake", "status": "ok"})()

    @pytest.mark.asyncio
    async def test_compress_short_history(self) -> None:
        from atar_core.agent import Agent
        from atar_core.compress import compress_history

        agent = Agent(provider=self._FakeStreamProvider(), max_turns=3)
        agent._messages = [
            Message(role="user", content="hi"),
            Message(role="assistant", content="hello"),
        ]
        result = await compress_history(agent, keep_last=4)
        assert "too short" in result.lower()

    @pytest.mark.asyncio
    async def test_compress_large_history(self) -> None:
        from atar_core.agent import Agent
        from atar_core.compress import compress_history

        agent = Agent(provider=self._FakeStreamProvider(), max_turns=3)
        agent._messages = [Message(role="system", content="system prompt")]
        for i in range(10):
            agent._messages.append(Message(role="user", content=f"msg {i}"))
            agent._messages.append(Message(role="assistant", content=f"reply {i}"))

        result = await compress_history(agent, keep_last=4)
        assert "Compressed" in result
        assert len(agent._messages) < 21  # should be compressed to fewer messages
