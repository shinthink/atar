"""ATAR tool models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    session_id: str = ""
    task_id: str = ""
    working_directory: str = "."
    env: dict[str, str] = Field(default_factory=dict)
    sandbox: str = "local"


class ToolResult(BaseModel):
    success: bool = True
    output: str = ""
    error: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
