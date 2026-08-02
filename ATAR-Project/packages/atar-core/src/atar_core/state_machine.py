"""ATAR agent state machine — per Section 9.1 and ADR-002.

States:
    IDLE → UNDERSTANDING → RETRIEVING_CONTEXT → PLANNING → RISK_REVIEW
      ├── WAITING_APPROVAL
      └── EXECUTING → VERIFYING → COMPLETED | REPAIRING | BLOCKED | CANCELLED | FAILED

Invalid transitions raise StateMachineError. All transitions emit events via EventBus.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atar_core.event_bus import EventBus

from atar_models.events import ATAREvent, EventType


class AgentState(StrEnum):
    IDLE = "idle"
    UNDERSTANDING = "understanding"
    RETRIEVING_CONTEXT = "retrieving_context"
    PLANNING = "planning"
    RISK_REVIEW = "risk_review"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    REPAIRING = "repairing"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    FAILED = "failed"


# Allowed transitions from each state
TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.IDLE: {AgentState.UNDERSTANDING, AgentState.CANCELLED, AgentState.FAILED},
    AgentState.UNDERSTANDING: {
        AgentState.RETRIEVING_CONTEXT, AgentState.COMPLETED, AgentState.FAILED
    },
    AgentState.RETRIEVING_CONTEXT: {AgentState.PLANNING, AgentState.FAILED},
    AgentState.PLANNING: {AgentState.RISK_REVIEW, AgentState.FAILED},
    AgentState.RISK_REVIEW: {AgentState.WAITING_APPROVAL, AgentState.EXECUTING, AgentState.FAILED},
    AgentState.WAITING_APPROVAL: {AgentState.EXECUTING, AgentState.CANCELLED},
    AgentState.EXECUTING: {
        AgentState.VERIFYING, AgentState.BLOCKED, AgentState.CANCELLED, AgentState.FAILED
    },
    AgentState.VERIFYING: {AgentState.COMPLETED, AgentState.REPAIRING, AgentState.FAILED},
    AgentState.REPAIRING: {AgentState.EXECUTING, AgentState.FAILED},
    AgentState.COMPLETED: {AgentState.UNDERSTANDING},  # allow continue
    AgentState.BLOCKED: {AgentState.EXECUTING, AgentState.CANCELLED},
    AgentState.CANCELLED: set(),  # terminal
    AgentState.FAILED: {AgentState.IDLE},  # allow reset
}


class StateMachineError(Exception):
    """Raised when an invalid state transition is attempted."""


class AgentStateMachine:
    """Tracks agent state and validates transitions."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._state = AgentState.IDLE
        self._history: list[tuple[AgentState, AgentState]] = []
        self._event_bus = event_bus

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def history(self) -> list[tuple[AgentState, AgentState]]:
        return list(self._history)

    def can_transition(self, target: AgentState) -> bool:
        return target in TRANSITIONS.get(self._state, set())

    def transition(self, target: AgentState, **event_kwargs) -> ATAREvent | None:
        """Transition to target state. Raises StateMachineError if invalid."""
        if not self.can_transition(target):
            msg = f"Cannot transition from {self._state} to {target}"
            raise StateMachineError(msg)

        previous = self._state
        self._state = target
        self._history.append((previous, target))

        if self._event_bus is not None:
            event = ATAREvent(
                event_type=EventType(f"state_{target.value}"),
                metadata={
                    "previous_state": previous.value,
                    "target_state": target.value,
                    **event_kwargs,
                },
            )
            # Fire-and-forget — don't block on event handlers
            import asyncio
            asyncio.create_task(self._event_bus.emit(event))
            return event
        return None

    def force(self, target: AgentState) -> None:
        """Force a transition without validation. Use only for recovery."""
        self._history.append((self._state, target))
        self._state = target

    def reset(self) -> None:
        self._state = AgentState.IDLE
        self._history.clear()

    def is_terminal(self) -> bool:
        return self._state in {AgentState.COMPLETED, AgentState.CANCELLED, AgentState.FAILED}

    def is_active(self) -> bool:
        return not self.is_terminal() and self._state != AgentState.IDLE
