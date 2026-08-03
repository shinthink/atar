"""ATAR skill system — filesystem-based, agentskills.io-compatible, self-improving."""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import time
from dataclasses import dataclass, field

from atar_core.paths import _atar_home as atar_home

SKILLS_DIR = os.path.join(atar_home(), "skills")
SKILLS_PENDING_DIR = os.path.join(SKILLS_DIR, "_pending")
SKILLS_ARCHIVE_DIR = os.path.join(SKILLS_DIR, "_archive")
SKILLS_META_FILE = os.path.join(SKILLS_DIR, "_meta.json")

os.makedirs(SKILLS_PENDING_DIR, exist_ok=True)
os.makedirs(SKILLS_ARCHIVE_DIR, exist_ok=True)


@dataclass
class SkillMeta:
    name: str
    description: str = ""
    trigger_hints: list[str] = field(default_factory=list)
    created_from_session: str = ""
    created_at: float = 0.0
    times_used: int = 0
    last_used_at: float = 0.0
    status: str = "active"  # active, pending, archived
    corrections: int = 0


class SkillManager:
    def __init__(self) -> None:
        self._skills: dict[str, SkillMeta] = {}
        self._load_meta()

    def _load_meta(self) -> None:
        if os.path.exists(SKILLS_META_FILE):
            with open(SKILLS_META_FILE) as f:
                data = json.load(f)
            for name, d in data.items():
                self._skills[name] = SkillMeta(**d)

    def _save_meta(self) -> None:
        data = {n: dataclasses.asdict(s) for n, s in self._skills.items()}
        with open(SKILLS_META_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def list_active(self) -> list[SkillMeta]:
        return [s for s in self._skills.values() if s.status == "active"]

    def list_pending(self) -> list[SkillMeta]:
        return [s for s in self._skills.values() if s.status == "pending"]

    def list_all(self) -> list[SkillMeta]:
        return list(self._skills.values())

    def load_skill_md(self, name: str) -> str | None:
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
        return None

    def propose(self, name: str, content: str, description: str = "", session_id: str = "") -> bool:
        """Write skill draft to _pending — NEVER to active dir directly."""
        # Safety: reject writing to active skills dir
        if name in self._skills and self._skills[name].status == "active":
            return False
        pending_path = os.path.join(SKILLS_PENDING_DIR, name)
        os.makedirs(pending_path, exist_ok=True)
        with open(os.path.join(pending_path, "SKILL.md"), "w") as f:
            f.write(content)
        self._skills[name] = SkillMeta(
            name=name, description=description,
            created_from_session=session_id,
            created_at=time.time(), status="pending",
        )
        self._save_meta()
        return True

    def review(self, name: str, approve: bool) -> bool:
        """Promote pending skill to active, or delete pending."""
        if name not in self._skills or self._skills[name].status != "pending":
            return False
        if approve:
            # Move from _pending to active
            src = os.path.join(SKILLS_PENDING_DIR, name)
            dst = os.path.join(SKILLS_DIR, name)
            os.makedirs(dst, exist_ok=True)
            if os.path.exists(os.path.join(src, "SKILL.md")):
                shutil.move(os.path.join(src, "SKILL.md"), os.path.join(dst, "SKILL.md"))
            shutil.rmtree(src, ignore_errors=True)
            self._skills[name].status = "active"
        else:
            # Remove from _pending
            shutil.rmtree(os.path.join(SKILLS_PENDING_DIR, name), ignore_errors=True)
            del self._skills[name]
        self._save_meta()
        return True

    def delete(self, name: str) -> bool:
        """Archive skill — never hard-delete."""
        if name not in self._skills:
            return False
        src = os.path.join(SKILLS_DIR, name)
        dst = os.path.join(SKILLS_ARCHIVE_DIR, name)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
        self._skills[name].status = "archived"
        self._save_meta()
        return True

    def refine(self, name: str, new_content: str) -> bool:
        """Update skill content after refinement."""
        if name not in self._skills:
            return False
        path = os.path.join(SKILLS_DIR, name, "SKILL.md")
        if not os.path.exists(path):
            return False
        with open(path, "w") as f:
            f.write(new_content)
        self._skills[name].corrections = 0  # reset correction counter
        self._save_meta()
        return True

    def record_use(self, name: str) -> None:
        if name in self._skills:
            self._skills[name].times_used += 1
            self._skills[name].last_used_at = time.time()
            self._save_meta()

    def record_correction(self, name: str) -> int:
        """Record a correction. Returns total corrections count."""
        if name in self._skills:
            self._skills[name].corrections += 1
            self._save_meta()
            return self._skills[name].corrections
        return 0


# Global singleton
_skill_manager: SkillManager | None = None


def get_skill_manager() -> SkillManager:
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager
