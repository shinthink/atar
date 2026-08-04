"""Tests for memory nudge and skill improvement."""

from __future__ import annotations

import os
import time


class TestMemoryNudge:
    """Memory nudge logic."""

    def setup_method(self) -> None:
        from atar_core.memory_nudge import NUDGE_STATE_PATH
        if os.path.exists(NUDGE_STATE_PATH):
            os.unlink(NUDGE_STATE_PATH)

    def test_nudge_state_roundtrip(self) -> None:
        from atar_core.memory_nudge import NudgeState, _load_state, _save_state
        state = NudgeState(
            last_nudge_at=time.time(),
            last_review_at=time.time() - 3600,
            nudge_count=3,
            entries_at_last_review=10,
        )
        _save_state(state)
        loaded = _load_state()
        assert loaded.nudge_count == 3
        assert loaded.entries_at_last_review == 10

    def test_should_nudge_no_entries(self) -> None:
        from atar_core.memory_nudge import should_nudge
        # Should not nudge if there are few entries
        result = should_nudge()
        assert result is False

    def test_mark_reviewed(self) -> None:
        from atar_core.memory_nudge import _load_state, mark_reviewed
        mark_reviewed()
        state = _load_state()
        assert state.last_review_at > 0

    def test_get_nudge_summary_empty(self) -> None:
        from atar_core.memory_nudge import get_nudge_summary
        summary = get_nudge_summary()
        # May be None if no entries, or show 0 entries
        assert summary is None or "entries" in summary.lower()

    def test_get_nudge_stats(self) -> None:
        from atar_core.memory_nudge import get_nudge_stats
        stats = get_nudge_stats()
        assert "active_entries" in stats
        assert "total_nudges" in stats


class TestSkillImprovement:
    """Skill self-improvement logic."""

    def test_skill_stats_defaults(self) -> None:
        from atar_core.skill_improvement import SkillStats
        s = SkillStats(name="test-skill")
        assert s.success_rate == 1.0
        assert s.times_used == 0
        assert s.is_reliable is False
        assert s.needs_improvement is False

    def test_record_skill_success(self) -> None:
        from atar_core.skill_improvement import get_skill_stats, record_skill_use
        s = record_skill_use("test-success", success=True)
        assert s.times_used == 1
        assert s.times_succeeded == 1
        assert s.times_failed == 0

        s2 = get_skill_stats("test-success")
        assert s2.times_used == 1

    def test_record_skill_failure(self) -> None:
        from atar_core.skill_improvement import record_skill_use
        s = record_skill_use("test-fail", success=False, error="File not found: /tmp/x.txt")
        assert s.times_failed == 1
        assert "File not found" in s.last_error

    def test_success_rate(self) -> None:
        from atar_core.skill_improvement import record_skill_use
        s = record_skill_use("test-rate", success=True)
        s = record_skill_use("test-rate", success=True)
        s = record_skill_use("test-rate", success=False, error="timeout")
        assert s.success_rate == 2 / 3

    def test_needs_improvement_detection(self) -> None:
        from atar_core.skill_improvement import record_skill_use
        # 3 uses, only 1 success = 33% < 50%
        record_skill_use("test-bad", success=False, error="timeout after 30s")
        record_skill_use("test-bad", success=False, error="timeout after 30s")
        s = record_skill_use("test-bad", success=True)
        # 1/3 = 33% < 50%, should flag needs_improvement
        assert s.needs_improvement is True

    def test_suggest_improvement_pattern(self) -> None:
        from atar_core.skill_improvement import record_skill_use
        record_skill_use("test-pattern", success=False, error="timeout after 30s")
        record_skill_use("test-pattern", success=False, error="timeout after 30s")
        record_skill_use("test-pattern", success=False, error="timeout after 30s")
        s = record_skill_use("test-pattern", success=True)
        # Should have an improvement suggestion
        assert len(s.improvements) >= 1
        assert "timeout" in s.improvements[0]["what"]

    def test_is_reliable(self) -> None:
        from atar_core.skill_improvement import record_skill_use
        for _ in range(5):
            record_skill_use("test-reliable", success=True)
        s = record_skill_use("test-reliable", success=True)
        assert s.is_reliable is True

    def test_get_all_skill_stats(self) -> None:
        from atar_core.skill_improvement import get_all_skill_stats, record_skill_use
        record_skill_use("test-all", success=True)
        stats = get_all_skill_stats()
        assert "test-all" in stats

    def test_improvement_summary(self) -> None:
        from atar_core.skill_improvement import get_improvement_summary, record_skill_use
        record_skill_use("summ-test", success=True)
        record_skill_use("summ-test", success=True)
        record_skill_use("summ-test", success=True)
        record_skill_use("summ-test", success=True)
        summary = get_improvement_summary()
        assert summary is not None
        assert "Reliable" in summary or "Skill Health" in summary
