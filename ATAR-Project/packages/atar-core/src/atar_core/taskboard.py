"""ATAR task board + subagent delegation — per blueprint Section 18.

Durable task board tracks assignments and results.
Subagents are isolated Agent instances that run delegated tasks.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Ticket:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    prompt: str = ""
    agent_role: str = "default"
    status: TaskStatus = TaskStatus.QUEUED
    result: str = ""
    error: str = ""
    created: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished: datetime | None = None


class TaskBoard:
    def __init__(self) -> None:
        self._tickets: dict[str, Ticket] = {}
        self._history: list[Ticket] = []

    def submit(self, prompt: str, agent_role: str = "default") -> Ticket:
        t = Ticket(prompt=prompt, agent_role=agent_role)
        self._tickets[t.id] = t
        return t

    def start(self, ticket_id: str) -> Ticket | None:
        t = self._tickets.get(ticket_id)
        if t and t.status == TaskStatus.QUEUED:
            t.status = TaskStatus.RUNNING
        return t

    def complete(self, ticket_id: str, result: str) -> Ticket | None:
        t = self._tickets.get(ticket_id)
        if t:
            t.status = TaskStatus.DONE
            t.result = result
            t.finished = datetime.now(UTC)
            self._history.append(t)
            self._tickets.pop(ticket_id, None)
        return t

    def fail(self, ticket_id: str, error: str) -> Ticket | None:
        t = self._tickets.get(ticket_id)
        if t:
            t.status = TaskStatus.FAILED
            t.error = error
            t.finished = datetime.now(UTC)
            self._history.append(t)
            self._tickets.pop(ticket_id, None)
        return t

    def status(self) -> dict[str, int]:
        return {
            "queued": sum(1 for t in self._tickets.values() if t.status == TaskStatus.QUEUED),
            "running": sum(1 for t in self._tickets.values() if t.status == TaskStatus.RUNNING),
            "done": len(self._history),
        }

    def active(self) -> list[Ticket]:
        return list(self._tickets.values())


class Delegator:
    """Runs delegated tasks in isolated agent instances."""

    def __init__(self, provider_factory, task_board: TaskBoard | None = None) -> None:
        self._provider_factory = provider_factory
        self.board = task_board or TaskBoard()

    async def delegate(
        self, prompt: str, role: str = "default", system_prompt: str = ""
    ) -> str:
        ticket = self.board.submit(prompt, role)
        self.board.start(ticket.id)

        try:
            from atar_core.agent import Agent, StreamCallbacks

            provider = self._provider_factory()
            sp = system_prompt or f"You are a {role} agent. Complete the task concisely."
            agent = Agent(provider=provider, system_prompt=sp, max_turns=3)

            response = await agent.run(prompt, StreamCallbacks())
            if response and response.text:
                self.board.complete(ticket.id, response.text)
                return response.text

            self.board.fail(ticket.id, "No response")
            return "No response from agent."
        except Exception as e:
            self.board.fail(ticket.id, str(e))
            return f"Error: {e}"

    async def delegate_parallel(
        self, tasks: list[tuple[str, str]], system_prompt: str = ""
    ) -> list[tuple[str, str]]:
        """Run multiple tasks in parallel. Returns [(prompt, result), ...]."""
        async def _run(prompt: str, role: str) -> tuple[str, str]:
            result = await self.delegate(prompt, role, system_prompt)
            return (prompt, result)

        coros = [_run(prompt, role) for prompt, role in tasks]
        return await asyncio.gather(*coros)
