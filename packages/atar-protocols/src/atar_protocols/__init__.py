"""ATAR Core Protocols — Abstract interfaces for all ATAR components.

Per the blueprint (Section 4.3, 6.6, 11):
- Every provider implements ``ModelProvider``.
- Every tool implements ``Tool``.
- Every storage backend implements ``SessionRepository``.
- Every sandbox implements ``ExecutionBackend``.

These protocols live in ``atar-protocols`` so that:
- ``atar-core`` can import and use them without importing concrete implementations.
- ``atar-tui`` never imports provider, sandbox, or tool implementations directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from atar_models.model_events import ModelEvent
from atar_models.requests import ModelRequest, TokenCountRequest
from atar_models.responses import ModelResponse, ProviderCapabilities, ProviderHealth
from atar_models.tools import ToolContext, ToolResult


@runtime_checkable
class ModelProvider(Protocol):
    """Provider protocol — every AI provider adapter implements this."""

    provider_id: str

    async def capabilities(self) -> ProviderCapabilities: ...
    async def list_models(self) -> list[str]: ...
    async def complete(self, request: ModelRequest) -> ModelResponse: ...
    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]: ...
    async def count_tokens(self, request: TokenCountRequest) -> int: ...
    async def health_check(self) -> ProviderHealth: ...


@runtime_checkable
class Tool(Protocol):
    """Tool protocol — every tool implements this."""

    async def execute(self, context: ToolContext, arguments: dict[str, Any]) -> ToolResult: ...


@runtime_checkable
class SessionRepository(Protocol):
    """Storage protocol for session persistence."""

    async def get(self, session_id: str) -> dict[str, Any]: ...
    async def save(self, session: dict[str, Any]) -> None: ...
    async def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]: ...


@runtime_checkable
class ExecutionBackend(Protocol):
    """Sandbox/execution backend protocol."""

    async def run(
        self,
        command: str,
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 30.0,
    ) -> tuple[int, str, str]: ...
