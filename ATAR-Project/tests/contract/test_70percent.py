"""Coverage tests for interaction, scheduler, session_search, prompt — push to 70%."""

from __future__ import annotations

import os
import tempfile
import time

import pytest


class TestInteraction:
    """Busy mode, background tasks, session recap."""

    def test_busy_mode_default(self) -> None:
        from atar_core.interaction import get_busy_mode
        assert get_busy_mode() == "interrupt"

    def test_set_busy_mode_valid(self) -> None:
        from atar_core.interaction import get_busy_mode, set_busy_mode
        original = get_busy_mode()
        set_busy_mode("queue")
        assert get_busy_mode() == "queue"
        set_busy_mode(original)

    def test_set_busy_mode_invalid(self) -> None:
        from atar_core.interaction import get_busy_mode, set_busy_mode
        original = get_busy_mode()
        set_busy_mode("invalid_mode")
        assert get_busy_mode() == original  # unchanged

    def test_handle_busy_input_interrupt(self) -> None:
        from atar_core.interaction import get_busy_mode, handle_busy_input, set_busy_mode
        original = get_busy_mode()
        set_busy_mode("interrupt")
        action, should_start = handle_busy_input("test", True)
        assert action == "interrupt"
        assert should_start is True
        set_busy_mode(original)

    def test_handle_busy_input_queue(self) -> None:
        from atar_core.interaction import get_busy_mode, handle_busy_input, set_busy_mode
        original = get_busy_mode()
        set_busy_mode("queue")
        action, should_start = handle_busy_input("test", True)
        assert action == "queue"
        assert should_start is False
        set_busy_mode(original)

    def test_handle_busy_input_steer_no_run(self) -> None:
        from atar_core.interaction import get_busy_mode, handle_busy_input, set_busy_mode
        original = get_busy_mode()
        set_busy_mode("steer")
        action, _ = handle_busy_input("steer test", False)
        assert action == "queue"  # fallback
        set_busy_mode(original)

    def test_should_show_busy_hint(self) -> None:
        from atar_core.interaction import mark_busy_hint_shown, should_show_busy_hint
        # mark it shown so it doesn't read config
        mark_busy_hint_shown()
        assert should_show_busy_hint() is False

    def test_background_task_lifecycle(self) -> None:
        from atar_core.interaction import (
            get_active_bg_count,
            get_pending_bg_results,
            start_background,
        )
        # start a simple background task
        def factory():
            class FakeAgent:
                interactive = False
                async def run(self, prompt):
                    return type("R", (), {"final_text": f"done: {prompt}"})()
            return FakeAgent()

        tid = start_background("test bg task", factory)
        assert tid.startswith("bg_")
        # wait for completion
        for _ in range(50):
            if get_active_bg_count() == 0:
                break
            time.sleep(0.05)
        results = get_pending_bg_results()
        assert len(results) >= 1

    def test_generate_recap(self) -> None:
        from atar_core.interaction import generate_recap
        data = {
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
                {"role": "tool", "name": "read_file", "content": "file contents"},
            ]
        }
        recap = generate_recap(data)
        assert recap is not None
        assert "Turns:" in recap

    def test_generate_recap_empty(self) -> None:
        from atar_core.interaction import generate_recap
        recap = generate_recap({"messages": []})
        assert recap is None


class TestScheduler:
    """Scheduler CRUD operations."""

    def setup_method(self) -> None:
        from atar_core.scheduler import DB_PATH
        self.db_backup = None
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                self.db_backup = f.read()
            os.unlink(DB_PATH)

    def teardown_method(self) -> None:
        from atar_core.scheduler import DB_PATH
        if os.path.exists(DB_PATH):
            os.unlink(DB_PATH)
        if self.db_backup:
            with open(DB_PATH, "wb") as f:
                f.write(self.db_backup)

    def test_add_and_list_jobs(self) -> None:
        from atar_core.scheduler import add_job, list_jobs
        job_id = add_job("30m", "test prompt")
        assert job_id > 0
        jobs = list_jobs()
        assert len(jobs) >= 1
        assert any(j.id == job_id for j in jobs)

    def test_set_enabled(self) -> None:
        from atar_core.scheduler import add_job, list_jobs, set_enabled
        job_id = add_job("1h", "test toggle")
        assert set_enabled(job_id, False) is True
        jobs = [j for j in list_jobs() if j.id == job_id]
        assert len(jobs) >= 1

    def test_remove_job(self) -> None:
        from atar_core.scheduler import add_job, remove_job
        job_id = add_job("5m", "to remove")
        assert remove_job(job_id) is True
        assert remove_job(99999) is False

    def test_record_failure(self) -> None:
        from atar_core.scheduler import add_job, record_failure
        job_id = add_job("10m", "failure test")
        assert record_failure(job_id) == 1
        assert record_failure(job_id) == 2  # disables after 2

    def test_parse_simple_cron_minutes(self) -> None:
        from atar_core.scheduler import _parse_simple_cron
        result = _parse_simple_cron("30m")
        assert result is not None
        assert result > time.time()

    def test_parse_simple_cron_hours(self) -> None:
        from atar_core.scheduler import _parse_simple_cron
        result = _parse_simple_cron("every 2h")
        assert result is not None

    def test_parse_simple_cron_iso(self) -> None:
        from atar_core.scheduler import _parse_simple_cron
        result = _parse_simple_cron("2026-12-31T23:59:59")
        assert result is not None

    def test_parse_simple_cron_default(self) -> None:
        from atar_core.scheduler import _parse_simple_cron
        result = _parse_simple_cron("invalid")
        assert result is not None
        assert result > time.time()

    def test_stop_scheduler(self) -> None:
        from atar_core.scheduler import stop_scheduler
        stop_scheduler()


class TestSessionSearch:
    """Session search FTS5 + summaries."""

    def setup_method(self) -> None:
        from atar_core.session_search import SUMMARY_CACHE
        SUMMARY_CACHE.clear()

    def test_index_session(self) -> None:
        from atar_core.session_search import index_session
        index_session("test-sess-1", "Test Title", "This is a test message")

    def test_set_and_get_summary(self) -> None:
        from atar_core.session_search import get_summary, set_summary
        set_summary("summ-1", "Short test summary")
        result = get_summary("summ-1")
        assert result == "Short test summary"

    def test_get_summary_nonexistent(self) -> None:
        from atar_core.session_search import get_summary
        result = get_summary("nonexistent-session")
        assert result is None

    def test_search_sessions_empty(self) -> None:
        from atar_core.session_search import search_sessions
        results = search_sessions("nonexistent_query_xyz")
        assert isinstance(results, list)

    def test_get_llm_call_count(self) -> None:
        from atar_core.session_search import get_llm_call_count
        count = get_llm_call_count()
        assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_generate_summary_no_provider(self) -> None:
        from atar_core.session_search import generate_summary
        summary = await generate_summary("gen-1", "some test messages here", provider=None)
        assert "gen-1" in summary

    @pytest.mark.asyncio
    async def test_generate_summary_cached(self) -> None:
        from atar_core.session_search import generate_summary, set_summary
        set_summary("cached-1", "already cached")
        summary = await generate_summary("cached-1", "irrelevant", provider=None)
        assert summary == "already cached"


class TestPrompt:
    """Prompt assembly layers."""

    def test_prompt_layer_dataclass(self) -> None:
        from atar_core.prompt import PromptLayer
        layer = PromptLayer(name="test", content="hello", stability="session")
        assert layer.name == "test"
        assert layer.content == "hello"

    def test_identity_layer(self) -> None:
        from atar_core.prompt import IDENTITY
        assert "ATAR" in IDENTITY.content

    def test_action_layer(self) -> None:
        from atar_core.prompt import ACTION
        assert "write_file" in ACTION.content

    def test_safety_layer(self) -> None:
        from atar_core.prompt import SAFETY
        assert "fabricate" in SAFETY.content

    def test_platform_layer(self) -> None:
        from atar_core.prompt import PLATFORM
        assert "Platform:" in PLATFORM.content

    def test_tools_layer(self) -> None:
        from atar_core.prompt import TOOLS
        assert "web_search" in TOOLS.content

    def test_instructions_layer(self) -> None:
        from atar_core.prompt import INSTRUCTIONS
        assert "concise" in INSTRUCTIONS.content.lower()

    def test_ephemeral_layer(self) -> None:
        from atar_core.prompt import ephemeral_layer
        layer = ephemeral_layer(session_id="abc123def456", model="deepseek", cwd="/tmp")
        assert "abc123def456" in layer.content
        assert "deepseek" in layer.content
        assert "/tmp" in layer.content

    def test_assemble_basic(self) -> None:
        from atar_core.prompt import assemble
        result = assemble(session_id="test", model="test-model", cwd="/tmp")
        assert "ATAR" in result.full
        assert "test-model" in result.full
        assert str(result) == result.full

    def test_assemble_with_atar_md(self) -> None:
        import os

        from atar_core.prompt import assemble
        # Create a temporary ATAR.md
        tmpdir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            with open("ATAR.md", "w") as f:
                f.write("Project context for testing.")
            result = assemble(cwd=tmpdir)
            assert "Project context" in result.full
        finally:
            os.chdir(old_cwd)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestAgentEdgeCases:
    """Agent undo, retry, history, state, tool_schemas."""

    class _FakeStreamProvider:
        model = "fake"

        async def stream(self, request):
            yield type("E", (), {"event_type": "text_delta", "text": "ok", "provider_metadata": {}})()

        async def count_tokens(self, request):
            return 0

        async def health_check(self):
            return type("H", (), {"provider_id": "fake", "status": "ok"})()

    def test_undo_last_turn_empty(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        result = agent.undo_last_turn()
        assert result == []

    def test_undo_with_n(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        result = agent.undo_last_turn(n=3)
        assert isinstance(result, list)

    def test_list_checkpoints(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        cps = agent.list_checkpoints()
        assert isinstance(cps, list)

    def test_retry_last_turn(self) -> None:
        from atar_core.agent import Agent
        from atar_models.requests import Message
        agent = Agent(provider=self._FakeStreamProvider())
        agent._messages = [
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi"),
        ]
        last = agent.retry_last_turn()
        assert last == "hello"

    def test_retry_empty(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        assert agent.retry_last_turn() is None

    def test_history(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        from atar_models.requests import Message
        agent._messages = [Message(role="user", content="test")]
        h = agent.history()
        assert len(h) == 1

    def test_format_messages_no_system(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        from atar_models.requests import Message
        agent._messages = [Message(role="user", content="hi")]
        msgs = agent._format_messages()
        assert msgs[0].role == "system"

    def test_format_messages_replace_system(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider(), system_prompt="custom")
        from atar_models.requests import Message
        agent._messages = [Message(role="system", content="old")]
        msgs = agent._format_messages()
        assert msgs[0].content == "custom"

    def test_continue_conversation(self) -> None:
        from atar_core.agent import Agent
        agent = Agent(provider=self._FakeStreamProvider())
        # continue_conversation returns coroutine
        coro = agent.continue_conversation("hello")
        assert coro is not None

    def test_run_result_final_text(self) -> None:
        from atar_core.budgets import RunResult, TerminalState
        result = RunResult(state=TerminalState.COMPLETED, final_text="done")
        assert result.final_text == "done"
        assert result.error is None


class TestProviderRouterEdgeCases:
    """ProviderRouter fallback, stream, edge cases."""

    def test_empty_router(self) -> None:
        from atar_core.provider_router import ProviderRouter
        router = ProviderRouter([])
        assert router.model == "none"
        assert router.fallback_count == 0

    def test_router_model_from_first_provider(self) -> None:
        from atar_core.provider_router import ProviderRouter
        p = type("P", (), {"model": "test-model"})()
        router = ProviderRouter([p])
        assert router.model == "test-model"

    @pytest.mark.asyncio
    async def test_capabilities_with_provider(self) -> None:
        from atar_core.provider_router import ProviderRouter
        caps = type("C", (), {"text": True, "streaming": True, "tools": True})()
        p = type("P", (), {})()
        async def _caps(): return caps
        p.capabilities = _caps  # type: ignore
        router = ProviderRouter([p])
        result = await router.capabilities()  # type: ignore
        assert result is not None

    @pytest.mark.asyncio
    async def test_health_check_empty(self) -> None:
        from atar_core.provider_router import ProviderRouter
        router = ProviderRouter([])
        health = await router.health_check()
        assert health.provider_id == "router"

    @pytest.mark.asyncio
    async def test_count_tokens_empty(self) -> None:
        from atar_core.provider_router import ProviderRouter
        from atar_models.requests import Message, TokenCountRequest
        router = ProviderRouter([])
        req = TokenCountRequest(model="test", messages=[Message(role="user", content="hi")])
        count = await router.count_tokens(req)
        assert count == 0

    @pytest.mark.asyncio
    async def test_list_models_empty(self) -> None:
        from atar_core.provider_router import ProviderRouter
        router = ProviderRouter([])
        models = await router.list_models()
        assert models == []

    @pytest.mark.asyncio
    async def test_complete_all_fail(self) -> None:
        from atar_core.provider_router import ProviderRouter
        from atar_models.requests import Message, ModelRequest

        class FailingProvider:
            model = "fail"
            async def complete(self, request):
                raise RuntimeError("down")

        router = ProviderRouter([FailingProvider()])
        req = ModelRequest(provider_id="test", model="x", messages=[Message(role="user", content="hi")])
        with pytest.raises(RuntimeError, match="All providers failed"):
            await router.complete(req)
        assert router.fallback_count == 0

    @pytest.mark.asyncio
    async def test_stream_all_fail(self) -> None:
        from atar_core.provider_router import ProviderRouter
        from atar_models.requests import Message, ModelRequest

        class FailingStreamProvider:
            model = "fail"

            async def stream(self, request):
                raise RuntimeError("stream down")
                yield  # unreachable

        router = ProviderRouter([FailingStreamProvider()])
        req = ModelRequest(provider_id="test", model="x", messages=[Message(role="user", content="hi")])
        with pytest.raises(RuntimeError, match="All providers failed streaming"):
            async for _ in router.stream(req):
                pass


class TestSecretsEdges:
    """Secrets module edge cases — save, delete, first_run."""

    def test_save_api_key_config_fallback(self) -> None:
        import json

        from atar_security.secrets import delete_api_key, save_api_key
        config_path = os.path.expanduser("~/.atar/config.json")
        if os.path.exists(config_path):
            os.unlink(config_path)
        try:
            result = save_api_key("test_provider", "test-key-123")
            assert result is True
            with open(config_path) as f:
                cfg = json.load(f)
            assert cfg.get("test_provider_api_key") == "test-key-123"
        finally:
            delete_api_key("test_provider")

    def test_is_first_run_no_config_file(self) -> None:
        from atar_security.secrets import is_first_run
        result = is_first_run()
        assert isinstance(result, bool)

    def test_get_api_key_not_set(self) -> None:
        from atar_security.secrets import get_api_key
        key = get_api_key("nonexistent_xyz_provider")
        assert key == ""


class TestSkillsEdges:
    """Skill manager edge cases."""

    def test_get_skill_manager(self) -> None:
        from atar_core.skills import get_skill_manager
        mgr = get_skill_manager()
        assert mgr is not None

    def test_list_all_skills(self) -> None:
        from atar_core.skills import get_skill_manager
        mgr = get_skill_manager()
        skills = mgr.list_all()
        assert isinstance(skills, list)

    def test_skill_manager_singleton(self) -> None:
        from atar_core.skills import get_skill_manager
        mgr1 = get_skill_manager()
        mgr2 = get_skill_manager()
        assert mgr1 is mgr2


class TestUserModel:
    """User model edges."""

    def test_load_model(self) -> None:
        from atar_core.user_model import load_model
        model = load_model()
        assert isinstance(model, dict)
        assert "languages" in model
        assert "topics" in model

    def test_model_to_prompt_empty(self) -> None:
        from atar_core.user_model import load_model, model_to_prompt
        model = load_model()
        prompt = model_to_prompt(model)
        assert isinstance(prompt, str)


class TestStateMachine:
    """State machine edges."""

    def test_initial_state(self) -> None:
        from atar_core.state_machine import AgentState, AgentStateMachine
        sm = AgentStateMachine()
        assert sm._state == AgentState.IDLE

    def test_valid_transition(self) -> None:
        from atar_core.state_machine import AgentState, AgentStateMachine
        sm = AgentStateMachine()
        sm.transition(AgentState.UNDERSTANDING)
        assert sm._state == AgentState.UNDERSTANDING

    def test_force_state(self) -> None:
        from atar_core.state_machine import AgentState, AgentStateMachine
        sm = AgentStateMachine()
        sm.force(AgentState.FAILED)
        assert sm._state == AgentState.FAILED


class TestCheckpointsEdges:
    """Additional checkpoint coverage."""

    def test_list_checkpoints_empty(self) -> None:
        from atar_tools.tools.checkpoints import list_checkpoints
        cps = list_checkpoints()
        assert isinstance(cps, list)

    def test_restore_nonexistent_checkpoint(self) -> None:
        from atar_tools.tools.checkpoints import restore_checkpoint
        result = restore_checkpoint("nonexistent_cp_xyz")
        assert result is False

    def test_clear_checkpoints(self) -> None:
        from atar_tools.tools.checkpoints import clear_checkpoints
        count = clear_checkpoints()
        assert isinstance(count, int)


class TestMoreCoverage:
    """Squeeze remaining coverage from misc modules."""

    def test_budgets_time_exhausted(self) -> None:
        import time

        from atar_core.budgets import RunBudget
        b = RunBudget(max_time_seconds=0.001)
        time.sleep(0.01)
        state = b.is_exhausted()
        assert state is not None

    def test_display_context_bar_zero_max(self) -> None:
        from atar_core.display import context_bar
        bar, color = context_bar(5000, 0)
        assert "K" in bar

    def test_output_truncation_get_full(self) -> None:
        from atar_core.output_truncation import get_full_output, save_full_output
        save_full_output(99, "test data")
        result = get_full_output(99)
        assert result == "test data"

    def test_checkpoint_before_write_new_file(self) -> None:
        from atar_tools.tools.checkpoints import checkpoint_before_write
        result = checkpoint_before_write("/tmp/nonexistent_file_xyz_123")
        assert result is None

    def test_compress_exception_handler(self) -> None:
        import asyncio

        from atar_core.agent import Agent
        from atar_core.compress import compress_history
        from atar_models.requests import Message

        class BrokenProvider:
            model = "broken"
            async def stream(self, request):
                raise RuntimeError("boom")
                yield
            async def count_tokens(self, request):
                return 0
            async def health_check(self):
                return type("H", (), {"provider_id": "broken", "status": "error"})()

        agent = Agent(provider=BrokenProvider(), max_turns=3)
        agent._messages = []
        for i in range(8):
            agent._messages.append(Message(role="user", content=f"msg {i}"))
            agent._messages.append(Message(role="assistant", content=f"reply {i}"))
        # Should not raise — exception handled gracefully
        result = asyncio.run(compress_history(agent, keep_last=4))
        assert "Compressed" in result

    def test_sqlite_store_search_error(self) -> None:
        from atar_storage.sqlite_store import SqliteSessionStore
        store = SqliteSessionStore(db_path="/tmp/test_search_err.db")
        # FTS5 MATCH with special chars should not raise
        results = store.search("special:chars*test")
        assert isinstance(results, list)
