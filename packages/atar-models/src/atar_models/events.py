"""ATAR domain events — per Section 4.4 of the blueprint.

The core emits typed events. Interfaces subscribe and render them.
The TUI must never parse log strings to infer runtime state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    SESSION_STARTED = "session_started"
    PLAN_CREATED = "plan_created"
    PLAN_APPROVAL_REQUESTED = "plan_approval_requested"
    TASK_STARTED = "task_started"
    MODEL_REQUEST_STARTED = "model_request_started"
    MODEL_STREAM_DELTA = "model_stream_delta"
    TOOL_CALL_PROPOSED = "tool_call_proposed"
    TOOL_APPROVAL_REQUESTED = "tool_approval_requested"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_OUTPUT = "tool_call_output"
    FILE_CHANGED = "file_changed"
    TEST_RUN_COMPLETED = "test_run_completed"
    VERIFICATION_COMPLETED = "verification_completed"
    MEMORY_PROPOSED = "memory_proposed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SESSION_ENDED = "session_ended"


class ATAREvent(BaseModel):
    """Base event — every domain event extends this."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_id: UUID | None = None
    task_id: UUID | None = None
    correlation_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionStarted(ATAREvent):
    event_type: EventType = EventType.SESSION_STARTED


class ModelStreamDelta(ATAREvent):
    event_type: EventType = EventType.MODEL_STREAM_DELTA
    text: str = ""


class ToolCallProposed(ATAREvent):
    event_type: EventType = EventType.TOOL_CALL_PROPOSED
    tool_name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallOutput(ATAREvent):
    event_type: EventType = EventType.TOOL_CALL_OUTPUT
    tool_name: str = ""
    result: str = ""
    error: str | None = None


class TaskCompleted(ATAREvent):
    event_type: EventType = EventType.TASK_COMPLETED
    result: str = ""
    turns: int = 0


class TaskFailed(ATAREvent):
    event_type: EventType = EventType.TASK_FAILED
    error: str = ""
    turns: int = 0
