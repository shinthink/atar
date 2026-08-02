"""Fake AI provider server for contract testing.

Per blueprint Section 6.14 and research requirements: every provider must have
a fake server that implements the ModelProvider protocol for deterministic testing.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from atar_models.model_events import ModelEvent
from atar_models.requests import ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth


class FakeModelProvider:
    """Deterministic fake provider for testing. Implements ModelProvider protocol."""

    def __init__(
        self,
        provider_id: str = "fake",
        responses: list[str] | None = None,
        events: list[ModelEvent] | None = None,
        fail_on: int | None = None,
    ) -> None:
        self.provider_id = provider_id
        self._responses = responses or ["Fake response."]
        self._events = events or []
        self._fail_on = fail_on
        self._call_count = 0
        self.complete_calls: list[ModelRequest] = []
        self.stream_calls: list[ModelRequest] = []

    async def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            text=True,
            streaming=bool(self._events),
            tools=False,
            token_counting=False,
            model_listing=False,
        )

    async def list_models(self) -> list[str]:
        return ["fake-model-v1"]

    async def complete(self, request: ModelRequest) -> ModelResponse:
        self._call_count += 1
        self.complete_calls.append(request)

        if self._fail_on is not None and self._call_count >= self._fail_on:
            msg = f"Simulated failure on call {self._call_count}"
            raise RuntimeError(msg)

        idx = (self._call_count - 1) % len(self._responses)
        return ModelResponse(
            request_id=str(request.request_id),
            model=request.model or "fake-model-v1",
            text=self._responses[idx],
        )

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        self._call_count += 1
        self.stream_calls.append(request)

        if self._events:
            for event in self._events:
                await asyncio.sleep(0)
                yield event
        else:
            for char in self._responses[(self._call_count - 1) % len(self._responses)]:
                await asyncio.sleep(0)
                yield ModelEvent(event_type="text_delta", text=char)
            yield ModelEvent(event_type="response_completed", finish_reason="stop")

    async def count_tokens(self, request: TokenCountRequest) -> int:
        return sum(len(m.content.split()) for m in request.messages)

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            status="healthy",
            latency_ms=1.0,
        )
