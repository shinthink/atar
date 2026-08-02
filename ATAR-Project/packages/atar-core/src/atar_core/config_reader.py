"""ATAR config reader — delegates to secrets module."""

from __future__ import annotations

from atar_security.secrets import delete_api_key, get_api_key, is_first_run, save_api_key

__all__ = ["get_api_key", "save_api_key", "delete_api_key", "is_first_run"]
