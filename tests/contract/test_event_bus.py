"""Contract tests for EventBus — per ADR-002."""

from __future__ import annotations

import asyncio

import pytest
from atar_core.event_bus import EventBus
from atar_models.events import (
    ATAREvent,
    EventType,
    SessionStarted,
    TaskCompleted,
    TaskFailed,
)


@pytest.fixture
def bus() -> EventBus:
    return EventBus()


@pytest.fixture
def sample_event() -> ATAREvent:
    return SessionStarted()


async def test_emit_calls_subscriber(bus: EventBus, sample_event: ATAREvent) -> None:
    received: list[ATAREvent] = []

    async def handler(event: ATAREvent) -> None:
        received.append(event)

    bus.subscribe(EventType.SESSION_STARTED, handler)
    await bus.emit_and_wait(sample_event)

    assert len(received) == 1
    assert received[0].event_type == EventType.SESSION_STARTED


async def test_emit_and_wait_multiple_subscribers(bus: EventBus) -> None:
    received: list[str] = []

    async def h1(event: ATAREvent) -> None:
        received.append("h1")

    async def h2(event: ATAREvent) -> None:
        received.append("h2")

    bus.subscribe(EventType.TASK_COMPLETED, h1)
    bus.subscribe(EventType.TASK_COMPLETED, h2)
    await bus.emit_and_wait(TaskCompleted())

    assert len(received) == 2
    assert "h1" in received
    assert "h2" in received


async def test_emit_does_not_wait(bus: EventBus) -> None:
    received: list[str] = []
    started = asyncio.get_running_loop().create_future()

    async def handler(event: ATAREvent) -> None:
        received.append("called")
        started.set_result(True)

    bus.subscribe(EventType.TASK_FAILED, handler)
    await bus.emit(TaskFailed())

    # emit() is fire-and-forget, handler may not have run yet
    # Wait briefly for the task to complete
    await asyncio.wait_for(started, timeout=1.0)
    assert "called" in received


async def test_wildcard_receives_all_events(bus: EventBus) -> None:
    received: list[EventType] = []

    async def handler(event: ATAREvent) -> None:
        received.append(event.event_type)

    bus.on_any(handler)
    await bus.emit_and_wait(SessionStarted())
    await bus.emit_and_wait(TaskCompleted())

    assert EventType.SESSION_STARTED in received
    assert EventType.TASK_COMPLETED in received


async def test_subscriber_error_isolation(bus: EventBus) -> None:
    healthy_received: list[str] = []

    async def failing_handler(event: ATAREvent) -> None:
        msg = "simulated failure"
        raise RuntimeError(msg)

    async def healthy_handler(event: ATAREvent) -> None:
        healthy_received.append("ok")

    bus.subscribe(EventType.SESSION_STARTED, failing_handler)
    bus.subscribe(EventType.SESSION_STARTED, healthy_handler)
    await bus.emit_and_wait(SessionStarted())

    assert "ok" in healthy_received


async def test_subscriber_count(bus: EventBus) -> None:
    assert bus.subscriber_count() == 0

    async def h(event: ATAREvent) -> None:
        pass

    bus.subscribe(EventType.SESSION_STARTED, h)
    assert bus.subscriber_count(EventType.SESSION_STARTED) == 1

    bus.on_any(h)
    assert bus.subscriber_count(EventType.SESSION_STARTED) == 2
