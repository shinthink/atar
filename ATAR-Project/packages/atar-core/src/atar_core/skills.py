"""ATAR skills and plugins — self-improvement governance + hook system.

Per blueprint Section 19: Skill lifecycle: proposed → reviewed → sandbox_tested →
benchmarked → canary → active → monitored → revised/deprecated.
Plugin hooks: ordered, timeout, cancellation, failure isolation.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class SkillStatus(StrEnum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    TESTED = "tested"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class Skill:
    def __init__(self, name: str, prompt: str, description: str = "") -> None:
        self.name = name
        self.prompt = prompt
        self.description = description
        self.status = SkillStatus.PROPOSED
        self.benchmark_score: float | None = None
        self.created_at = datetime.now(UTC)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "prompt": self.prompt,
            "description": self.description,
            "status": self.status.value,
            "benchmark_score": self.benchmark_score,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> Skill:
        s = cls(d["name"], d["prompt"], d.get("description", ""))
        s.status = SkillStatus(d.get("status", "proposed"))
        s.benchmark_score = d.get("benchmark_score")
        return s


class SkillRegistry:
    def __init__(self, path: str = ".atar/skills.json") -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._skills: dict[str, Skill] = {}
        self._load()

    def propose(self, name: str, prompt: str, description: str = "") -> Skill:
        if name in self._skills:
            raise ValueError(f"Skill {name} exists")
        s = Skill(name, prompt, description)
        self._skills[name] = s
        self._flush()
        return s

    def review(self, name: str) -> Skill | None:
        s = self._skills.get(name)
        if s and s.status == SkillStatus.PROPOSED:
            s.status = SkillStatus.REVIEWED
            self._flush()
        return s

    def activate(self, name: str) -> Skill | None:
        s = self._skills.get(name)
        if s and s.status in (SkillStatus.REVIEWED, SkillStatus.TESTED):
            s.status = SkillStatus.ACTIVE
            self._flush()
        return s

    def deprecate(self, name: str) -> Skill | None:
        s = self._skills.get(name)
        if s:
            s.status = SkillStatus.DEPRECATED
            self._flush()
        return s

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_active(self) -> list[Skill]:
        return [s for s in self._skills.values() if s.status == SkillStatus.ACTIVE]

    def list_all(self) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.created_at)

    def _flush(self) -> None:
        with open(self.path, "w") as f:
            json.dump({n: s.to_dict() for n, s in self._skills.items()}, f, indent=2, default=str)

    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path) as f:
                data = json.load(f)
            for name, d in data.items():
                self._skills[name] = Skill.from_dict(d)


# ── Plugin Hooks ──

HookFn = Callable[[dict[str, Any]], Any]


class PluginHook:
    def __init__(self, name: str, fn: HookFn, priority: int = 0, timeout: float = 10.0) -> None:
        self.name = name
        self.fn = fn
        self.priority = priority
        self.timeout = timeout


class HookManager:
    def __init__(self) -> None:
        self._hooks: dict[str, list[PluginHook]] = {}

    def register(self, event: str, hook: PluginHook) -> None:
        self._hooks.setdefault(event, []).append(hook)
        self._hooks[event].sort(key=lambda h: -h.priority)

    def unregister(self, event: str, name: str) -> None:
        if event in self._hooks:
            self._hooks[event] = [h for h in self._hooks[event] if h.name != name]

    async def fire(self, event: str, data: dict[str, Any] | None = None) -> list[Any]:
        results: list[Any] = []
        for hook in self._hooks.get(event, []):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(hook.fn, data or {}), timeout=hook.timeout
                )
                results.append(result)
            except TimeoutError:
                results.append(f"timeout:{hook.name}")
            except Exception as e:
                results.append(f"error:{hook.name}:{e}")
        return results
