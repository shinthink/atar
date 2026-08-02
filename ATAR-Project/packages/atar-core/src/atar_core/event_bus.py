"""ATAR typed event bus — per ADR-002.

Provides async pub/sub for ATAREvent instances with:
- subscribe(event_type, callback) — register typed handler
- emit(event) — fire-and-forget publish
- emit_and_wait(event) — publish and await all subscribers
- Subscriber error isolation — one failing subscriber does not break others
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable

from atar_models.events import ATAREvent, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[ATAREvent], Awaitable[None]]


class EventBus:
    """Typed async event bus. Subscribers register by event type string."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._wildcard: list[EventHandler] = []  # receives ALL events

    def subscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        """Register handler for a specific event type. Use '*' for all events."""
        key = event_type if isinstance(event_type, str) else event_type.value
        self._subscribers[key].append(handler)

    def on_any(self, handler: EventHandler) -> None:
        """Register handler that receives every event regardless of type."""
        self._wildcard.append(handler)

    async def emit(self, event: ATAREvent) -> None:
        """Fire-and-forget: schedule all handlers without waiting."""
        handlers = self._resolve_handlers(event)
        for handler in handlers:
            asyncio.create_task(self._safe_invoke(handler, event))

    async def emit_and_wait(self, event: ATAREvent) -> None:
        """Publish and await all subscribers."""
        handlers = self._resolve_handlers(event)
        tasks = [asyncio.create_task(self._safe_invoke(h, event)) for h in handlers]
        if tasks:
            await asyncio.gather(*tasks)

    def _resolve_handlers(self, event: ATAREvent) -> list[EventHandler]:
        event_key = event.event_type.value
        handlers: list[EventHandler] = []
        handlers.extend(self._wildcard)
        handlers.extend(self._subscribers.get(event_key, []))
        return handlers

    async def _safe_invoke(self, handler: EventHandler, event: ATAREvent) -> None:
        try:
            await handler(event)
        except Exception:
            logger.exception("Event handler failed for %s", event.event_type)

    def subscriber_count(self, event_type: EventType | str | None = None) -> int:
        """Return subscriber count. If event_type is None, return total."""
        if event_type is None:
            return len(self._wildcard) + sum(len(v) for v in self._subscribers.values())
        key = event_type if isinstance(event_type, str) else event_type.value
        return len(self._wildcard) + len(self._subscribers.get(key, []))
