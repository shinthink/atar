"""Phase 1: Memory system + session search tests."""

from __future__ import annotations

from atar_core.memory import count_active, create_entry, forget_entry, get_entries, supersede_entry
from atar_core.session_search import get_summary, index_session, search_sessions, set_summary


class TestMemoryCRUD:
    def test_create_and_retrieve(self, tmp_path):
        eid = create_entry("preference", "User prefers dark theme")
        assert eid is not None
        entries = get_entries()
        assert any(e.content == "User prefers dark theme" for e in entries)

    def test_secret_filtering(self):
        eid = create_entry("test", "my key is sk-abc123def456ghi789jkl012mno345pqr678stu")
        assert eid is None  # rejected

    def test_supersede_preserves_history(self):
        eid = create_entry("fact", "Old fact")
        assert eid is not None
        new_id = supersede_entry(eid, "Updated fact")
        assert new_id is not None
        assert new_id != eid
        # Old entry still exists but superseded
        all_entries = get_entries(active_only=False)
        ids = {e.id for e in all_entries}
        assert eid in ids
        assert new_id in ids
        # Only new entry is active
        active = get_entries(active_only=True)
        assert all(e.id != eid for e in active)

    def test_forget_never_deletes(self):
        eid = create_entry("fact", "Something to forget")
        count_before = len(get_entries(active_only=False))
        ok = forget_entry(eid)
        assert ok
        count_after = len(get_entries(active_only=False))
        # Should have MORE entries (new tombstone added)
        assert count_after >= count_before + 1

    def test_category_filter(self):
        create_entry("preference", "Likes Python")
        create_entry("decision", "Use uv for packaging")
        prefs = get_entries(category="preference")
        assert all(e.category == "preference" for e in prefs)

    def test_count_active(self):
        # Clean existing entries from other tests
        existing = count_active()
        eid = create_entry("fact", "Temporary")
        assert count_active() == existing + 1
        forget_entry(eid)
        # After forget, active count goes up (tombstone added)
        assert count_active() == existing + 1


class TestSessionSearch:
    def test_index_and_search(self):
        index_session("sess-001", "Test Session", "hello world python coding")
        index_session("sess-002", "Other", "machine learning deep learning")
        results = search_sessions("python")
        assert any(r["session_id"] == "sess-001" for r in results), f"Got: {results}"

    def test_search_no_results(self):
        results = search_sessions("xyzznonexistent123")
        assert len(results) == 0

    def test_summary_cached(self):
        set_summary("sess-003", "Cached one-liner summary")
        s = get_summary("sess-003")
        assert s == "Cached one-liner summary"
