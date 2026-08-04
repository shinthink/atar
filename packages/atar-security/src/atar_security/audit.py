"""ATAR audit logging — correlation-ID based audit trail."""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar

logger = logging.getLogger("atar.audit")

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def set_correlation_id(cid: str | None = None) -> str:
    """Set correlation ID for the current async context. Returns the ID."""
    cid = cid or uuid.uuid4().hex[:12]
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    return _correlation_id.get()


def log_action(action: str, **details: object) -> None:
    """Log an auditable action with correlation ID."""
    cid = get_correlation_id()
    if cid:
        logger.info("%s [correlation=%s] %s", action, cid, details)
    else:
        logger.info("%s %s", action, details)
