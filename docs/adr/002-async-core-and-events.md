# ADR-002: Async Core and Typed Event System

## Status
Accepted

## Context
ATAR Terminal v1.0 requires an async-native agent runtime per the blueprint Section 4.3. Every I/O operation — provider calls, tool execution, file operations, network requests — must be async with structured concurrency, cancellation scopes, timeouts, parent task tracking, correlation IDs, cleanup behavior, and final state persistence.

The core must emit typed events (Section 4.4) that the TUI subscribes to, never requiring the TUI to parse log strings. Events include: SessionStarted, PlanCreated, TaskStarted, ModelStreamDelta, ToolCallProposed, ToolCallOutput, TaskCompleted, TaskFailed, and others.

## Decision
Use **AnyIO** as the structured concurrency layer over Python's asyncio, with a typed event bus following the observer pattern.

### Event Bus Architecture
```
Publisher (Agent Core)
    ↓ emit(ATAREvent)
EventBus (AnyIO memory stream or queue)
    ↓ dispatch to subscribers
Subscriber 1 (TUI)     Subscriber 2 (Audit)    Subscriber 3 (Storage)
```

### Key Design Decisions
1. **AnyIO** for task groups, cancellation scopes, and timeouts — provides a clean API over asyncio with trio-style structured concurrency (blueprint Section 4.3 requirement).
2. **Typed events** using `atar_models.events.ATAREvent` Pydantic models — every event has `event_id`, `event_type`, `timestamp`, `session_id`, `task_id`, `correlation_id`.
3. **EventBus** as a simple async pub/sub with:
   - `subscribe(event_type, callback)` — register a handler
   - `emit(event)` — fire-and-forget publish
   - `emit_and_wait(event)` — publish and await all handlers
   - Subscriber error isolation — one failing subscriber does not break others
4. **Correlation ID** propagation through all async tasks using context variables (`contextvars`).

### Package Layout
```
packages/atar-core/src/atar_core/
├── event_bus.py      — EventBus with pub/sub
├── state_machine.py  — Agent state transitions
├── runtime.py         — Async task manager with AnyIO
└── correlation.py     — Correlation ID context
```

### State Machine (Section 9.1)
```
IDLE → UNDERSTANDING → RETRIEVING_CONTEXT → PLANNING → RISK_REVIEW
  ├── WAITING_APPROVAL
  └── EXECUTING → VERIFYING → COMPLETED | REPAIRING | BLOCKED | CANCELLED | FAILED
```

States are string enums persisted on each transition. Invalid transitions raise typed errors.

## Consequences
- All future core code must be async-native with AnyIO.
- TUI code may be sync or async (Textual is async-compatible but not required to be async).
- Storage layer must use async SQLAlchemy with AnyIO-compatible drivers.
- Every provider call, tool call, and I/O operation gets a correlation ID.
- State transitions are evented and auditable.

## Alternatives Considered
1. **Pure asyncio without AnyIO** — rejected because no built-in structured concurrency, task groups, or cancellation scopes in Python 3.12 stdlib.
2. **Trio** — rejected in favor of AnyIO which provides trio-like semantics on asyncio, preserving ecosystem compatibility.
3. **No event bus (direct function calls)** — rejected because the TUI must subscribe to events without tight coupling (Section 4.4 requirement).
4. **Third-party message broker (Redis, NATS)** — rejected for v1.0 because ATAR is local-first with no required network service.

## References
- Blueprint Section 4.3 (Async-native requirement)
- Blueprint Section 4.4 (Event-driven UI boundary)
- Blueprint Section 9.1 (Agent state machine)
- https://anyio.readthedocs.io/en/stable/
- https://docs.python.org/3/library/contextvars.html
- https://docs.python.org/3/library/asyncio-task.html
