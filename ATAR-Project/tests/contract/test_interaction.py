"""UI-2: Interaction tests."""

from __future__ import annotations

from atar_core.interaction import (
    BUSY_MODES, generate_recap, get_busy_mode,
    handle_busy_input, set_busy_mode, start_background,
)


class TestBusyMode:
    def test_default_is_interrupt(self):
        set_busy_mode("interrupt")
        assert get_busy_mode() == "interrupt"

    def test_set_and_get(self):
        set_busy_mode("queue")
        assert get_busy_mode() == "queue"
        set_busy_mode("interrupt")  # reset

    def test_invalid_mode_ignored(self):
        before = get_busy_mode()
        set_busy_mode("invalid")
        assert get_busy_mode() == before

    def test_steer_fallback_when_not_running(self):
        set_busy_mode("steer")
        action, _ = handle_busy_input("test", is_running=False)
        assert action == "queue"
        set_busy_mode("interrupt")

    def test_steer_works_when_running(self):
        set_busy_mode("steer")
        action, _ = handle_busy_input("test", is_running=True)
        assert action == "steer"
        set_busy_mode("interrupt")


class TestSessionRecap:
    def test_generates_turn_count(self):
        data = {"messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "help"},
            {"role": "assistant", "content": "sure"},
        ]}
        recap = generate_recap(data)
        assert recap is not None
        assert "Turns: 2" in recap

    def test_empty_session(self):
        recap = generate_recap({"messages": []})
        assert recap is None

    def test_shows_tools_used(self):
        data = {"messages": [
            {"role": "user", "content": "x"},
            {"role": "tool", "name": "write_file"},
            {"role": "assistant", "content": "done"},
        ]}
        recap = generate_recap(data)
        assert "write_file" in recap
