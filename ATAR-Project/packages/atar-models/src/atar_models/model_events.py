"""ATAR streaming events — normalized per Section 6.8."""

from __future__ import annotations

from pydantic import BaseModel


class ModelEvent(BaseModel):
    """Normalized streaming event — adapters translate provider events into these."""
    event_type: str = ""
    text: str = ""
    tool_call: dict | None = None
    usage: dict | None = None
    finish_reason: str | None = None
    provider_metadata: dict | None = None
    error: str | None = None
