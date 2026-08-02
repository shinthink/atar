"""ATAR plan and task models — per blueprint Section 10."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(BaseModel):
    id: str = ""
    title: str = ""
    description: str = ""
    risk: RiskLevel = RiskLevel.LOW
    status: TaskStatus = TaskStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)
    agent: str = "default"
    evidence: str = ""
    output: str = ""

    @classmethod
    def from_text(cls, text: str) -> Task:
        """Parse a task from a single line of text."""
        text = text.strip().lstrip("- ").lstrip("0123456789. ")
        risk = RiskLevel.LOW
        if "[HIGH]" in text:
            risk = RiskLevel.HIGH
        elif "[MEDIUM]" in text:
            risk = RiskLevel.MEDIUM
        elif "[LOW]" in text:
            risk = RiskLevel.LOW
        return cls(title=text, risk=risk)


class Plan(BaseModel):
    title: str = ""
    goal: str = ""
    tasks: list[Task] = Field(default_factory=list)
    evidence_required: bool = False

    @property
    def pending(self) -> list[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    @property
    def approved(self) -> list[Task]:
        return [t for t in self.tasks if t.status == TaskStatus.APPROVED]

    @classmethod
    def parse(cls, raw: str, goal: str = "") -> Plan:
        """Parse a plan from model output. Expects markdown list format."""
        tasks = []
        title = goal
        for line in raw.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not title:
                title = line[2:]
            elif line.startswith("- ") or (line and line[0].isdigit()):
                tasks.append(Task.from_text(line))
        return cls(title=title, goal=goal, tasks=tasks)

    def approve_all(self) -> None:
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.APPROVED

    def high_risk_tasks(self) -> list[Task]:
        return [t for t in self.tasks if t.risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)]
