"""Phase 2: Skill system tests."""

from __future__ import annotations

import pytest
from atar_core.skills import get_skill_manager


@pytest.fixture(autouse=True)
def _isolated_skills(monkeypatch, tmp_path):
    """Use temp dir for skill storage."""
    skills_dir = tmp_path / 'skills'
    pending = skills_dir / '_pending'
    archive = skills_dir / '_archive'
    pending.mkdir(parents=True)
    archive.mkdir(parents=True)
    monkeypatch.setattr('atar_core.skills.SKILLS_DIR', str(skills_dir))
    monkeypatch.setattr('atar_core.skills.SKILLS_PENDING_DIR', str(pending))
    monkeypatch.setattr('atar_core.skills.SKILLS_ARCHIVE_DIR', str(archive))
    monkeypatch.setattr('atar_core.skills.SKILLS_META_FILE', str(skills_dir / '_meta.json'))
    from atar_core import skills
    skills._skill_manager = None
    yield


class TestSkillSystem:
    def test_propose_writes_to_pending_not_active(self):
        mgr = get_skill_manager()
        content = '--- name: test-skill description: A test --- # Test Steps here.'
        ok = mgr.propose('test-skill', content, description='A test')
        assert ok
        pending = mgr.list_pending()
        active = mgr.list_active()
        assert any(s.name == 'test-skill' for s in pending)
        assert not any(s.name == 'test-skill' for s in active)

    def test_review_promotes_to_active(self):
        mgr = get_skill_manager()
        mgr.propose('test-skill', 'content', 'desc')
        ok = mgr.review('test-skill', approve=True)
        assert ok
        assert any(s.name == 'test-skill' for s in mgr.list_active())
        assert not any(s.name == 'test-skill' for s in mgr.list_pending())

    def test_review_rejected_removes_pending(self):
        mgr = get_skill_manager()
        mgr.propose('test-skill', 'content', 'desc')
        ok = mgr.review('test-skill', approve=False)
        assert ok
        assert not any(s.name == 'test-skill' for s in mgr.list_all())

    def test_delete_archives_not_hard_deletes(self):
        mgr = get_skill_manager()
        mgr.propose('test-skill', 'content', 'desc')
        mgr.review('test-skill', approve=True)
        ok = mgr.delete('test-skill')
        assert ok
        active = mgr.list_active()
        assert not any(s.name == 'test-skill' for s in active)

    def test_usage_tracking(self):
        mgr = get_skill_manager()
        mgr.propose('test-skill', 'content', 'desc')
        mgr.review('test-skill', approve=True)
        mgr.record_use('test-skill')
        mgr.record_use('test-skill')
        s = [x for x in mgr.list_active() if x.name == 'test-skill'][0]
        assert s.times_used == 2

    def test_correction_tracking(self):
        mgr = get_skill_manager()
        mgr.propose('test-skill', 'content', 'desc')
        mgr.review('test-skill', approve=True)
        assert mgr.record_correction('test-skill') == 1
        assert mgr.record_correction('test-skill') == 2

    def test_load_skill_md(self):
        mgr = get_skill_manager()
        content = '# Hello World Step 1: Do X.'
        mgr.propose('test-skill', content)
        mgr.review('test-skill', approve=True)
        loaded = mgr.load_skill_md('test-skill')
        assert loaded == content

    def test_direct_write_to_active_blocked(self):
        mgr = get_skill_manager()
        mgr.propose('test-skill', 'content', 'desc')
        mgr.review('test-skill', approve=True)
        ok = mgr.propose('test-skill', 'new content', 'new desc')
        assert not ok
