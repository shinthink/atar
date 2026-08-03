"""Phase 3: Scheduler tests."""

from __future__ import annotations

from atar_core.scheduler import add_job, list_jobs, record_failure, remove_job, set_enabled


class TestScheduler:
    def test_add_and_list(self):
        jid = add_job("5m", "test prompt")
        assert jid > 0
        jobs = list_jobs()
        assert any(j.id == jid for j in jobs)

    def test_remove_job(self):
        jid = add_job("5m", "to remove")
        ok = remove_job(jid)
        assert ok
        jobs = list_jobs()
        assert not any(j.id == jid for j in jobs)

    def test_pause_resume(self):
        jid = add_job("5m", "pausable")
        ok = set_enabled(jid, False)
        assert ok
        jobs = list_jobs()
        job = [j for j in jobs if j.id == jid][0]
        assert not job.enabled
        set_enabled(jid, True)
        jobs = list_jobs()
        job = [j for j in jobs if j.id == jid][0]
        assert job.enabled

    def test_failure_disables_after_two(self):
        jid = add_job("5m", "failing job")
        assert record_failure(jid) == 1
        # Should still be enabled after 1 failure
        jobs = list_jobs()
        job = [j for j in jobs if j.id == jid][0]
        assert job.enabled
        assert record_failure(jid) == 2
        # Should be disabled after 2 failures
        jobs = list_jobs()
        job = [j for j in jobs if j.id == jid][0]
        assert not job.enabled
