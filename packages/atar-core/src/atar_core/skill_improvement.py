"""ATAR skill self-improvement — usage tracking, success/failure learning, auto-update.

Hermes-style: skills improve themselves by tracking what works and what doesn't.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from atar_core.paths import _atar_home as atar_home

SKILL_STATS_PATH = os.path.join(atar_home(), "skill_stats.json")


@dataclass
class SkillStats:
    """Per-skill usage statistics and improvement data."""
    name: str = ""
    times_used: int = 0
    times_succeeded: int = 0
    times_failed: int = 0
    last_used_at: float = 0.0
    last_error: str = ""
    common_failures: list[str] = field(default_factory=list)  # last 5 error messages
    improvements: list[dict] = field(default_factory=list)  # [{at: ts, what: "..."}]
    version: int = 0

    @property
    def success_rate(self) -> float:
        if self.times_used == 0:
            return 1.0
        return self.times_succeeded / self.times_used

    @property
    def is_reliable(self) -> bool:
        return self.times_used >= 3 and self.success_rate >= 0.7

    @property
    def needs_improvement(self) -> bool:
        return self.times_used >= 3 and self.success_rate < 0.5

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "times_used": self.times_used,
            "times_succeeded": self.times_succeeded,
            "times_failed": self.times_failed,
            "last_used_at": self.last_used_at,
            "last_error": self.last_error,
            "common_failures": self.common_failures[-5:],
            "improvements": self.improvements[-10:],
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SkillStats:
        return cls(
            name=d.get("name", ""),
            times_used=d.get("times_used", 0),
            times_succeeded=d.get("times_succeeded", 0),
            times_failed=d.get("times_failed", 0),
            last_used_at=d.get("last_used_at", 0.0),
            last_error=d.get("last_error", ""),
            common_failures=d.get("common_failures", []),
            improvements=d.get("improvements", []),
            version=d.get("version", 0),
        )


def _load_all_stats() -> dict[str, SkillStats]:
    try:
        with open(SKILL_STATS_PATH) as f:
            raw = json.load(f)
        return {k: SkillStats.from_dict(v) for k, v in raw.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_all_stats(stats: dict[str, SkillStats]) -> None:
    os.makedirs(os.path.dirname(SKILL_STATS_PATH), exist_ok=True)
    with open(SKILL_STATS_PATH, "w") as f:
        json.dump({k: v.to_dict() for k, v in stats.items()}, f, indent=2)


def get_skill_stats(skill_name: str) -> SkillStats:
    """Get or create stats for a skill."""
    stats = _load_all_stats()
    if skill_name not in stats:
        stats[skill_name] = SkillStats(name=skill_name)
    return stats[skill_name]


def record_skill_use(skill_name: str, success: bool, error: str = "") -> SkillStats:
    """Record a skill usage event. Returns updated stats."""
    stats_dict = _load_all_stats()
    s = stats_dict.get(skill_name, SkillStats(name=skill_name))

    s.times_used += 1
    s.last_used_at = time.time()
    if success:
        s.times_succeeded += 1
        s.last_error = ""
    else:
        s.times_failed += 1
        s.last_error = error[:200]
        if error:
            s.common_failures.append(error[:200])
            if len(s.common_failures) > 5:
                s.common_failures = s.common_failures[-5:]

        # Auto-suggest improvement if success rate is low
        if s.needs_improvement:
            suggestion = suggest_improvement(skill_name, s)
            if suggestion:
                s.improvements.append({
                    "at": time.time(),
                    "what": suggestion,
                })

    stats_dict[skill_name] = s
    _save_all_stats(stats_dict)
    return s


def suggest_improvement(skill_name: str, stats: SkillStats) -> str | None:
    """Analyze failures and suggest an improvement. Returns suggestion or None."""
    if not stats.common_failures:
        return None

    # Analyze common failure patterns
    errors = stats.common_failures
    patterns: dict[str, int] = {}

    for err in errors:
        err_lower = err.lower()
        if "not found" in err_lower or "no such file" in err_lower:
            patterns["pre-check file existence before operating"] = patterns.get("pre-check file existence before operating", 0) + 1
        elif "timeout" in err_lower:
            patterns["increase timeout or retry with backoff"] = patterns.get("increase timeout or retry with backoff", 0) + 1
        elif "permission" in err_lower:
            patterns["add permission check before operation"] = patterns.get("add permission check before operation", 0) + 1
        elif "connection" in err_lower or "refused" in err_lower:
            patterns["add connectivity check + retry logic"] = patterns.get("add connectivity check + retry logic", 0) + 1
        elif "rate" in err_lower or "limit" in err_lower:
            patterns["add rate limiting / backoff"] = patterns.get("add rate limiting / backoff", 0) + 1

    if patterns:
        best = max(patterns, key=lambda k: patterns[k])
        if patterns[best] >= 2:  # at least 2 occurrences
            return best

    return None


def get_all_skill_stats() -> dict[str, SkillStats]:
    """Get all skill stats for display."""
    return _load_all_stats()


def get_improvement_summary() -> str | None:
    """Generate a summary of skills needing improvement."""
    all_stats = _load_all_stats()
    if not all_stats:
        return None

    lines = ["[bold]Skill Health[/]", ""]
    needs_attention = []
    reliable = []

    for _name, s in sorted(all_stats.items()):
        if s.needs_improvement:
            needs_attention.append(s)
        elif s.is_reliable:
            reliable.append(s)

    if needs_attention:
        lines.append("[yellow]⚠ Needs improvement:[/]")
        for s in needs_attention:
            lines.append(f"  {s.name}: {s.success_rate:.0%} success ({s.times_used} uses)")
            if s.last_error:
                lines.append(f"    Last error: [dim]{s.last_error[:60]}[/]")

    if reliable:
        lines.append("")
        lines.append("[#4ADE80]✓ Reliable:[/]")
        for s in reliable[:5]:
            lines.append(f"  {s.name}: {s.success_rate:.0%} ({s.times_used} uses)")

    if not needs_attention and not reliable:
        lines.append("[dim]No skills have enough usage data yet.[/]")

    return "\n".join(lines)
