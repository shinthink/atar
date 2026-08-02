"""ATAR secrets manager — per ADR-004."""

from __future__ import annotations

import os
import re


class SecretRef:
    """Reference to a secret stored externally, never in config files."""

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._value: str | None = None

    def __repr__(self) -> str:
        return f"SecretRef({self.uri})"


class SecretsManager:
    """Resolves secrets from OS keyring, env vars, or encrypted file."""

    def resolve(self, key: str, env_var: str | None = None) -> str | None:
        """Resolve a secret. Priority: env var → keyring → None."""
        if env_var:
            val = os.environ.get(env_var)
            if val:
                return val

        api_key_env = f"ATAR_{key.upper()}_API_KEY"
        val = os.environ.get(api_key_env) or os.environ.get("ATAR_API_KEY")
        if val:
            return val

        try:
            import keyring
            val = keyring.get_password("atar", key)
            if val:
                return val
        except ImportError:
            pass

        return None

    @staticmethod
    def redact(text: str) -> str:
        """Redact common credential patterns from text."""
        patterns = [
            (r'sk-[a-zA-Z0-9_-]{20,}', "sk-***REDACTED***"),
            (r'sk-ant-[a-zA-Z0-9_-]{20,}', "sk-ant-***REDACTED***"),
            (r'Bearer [a-zA-Z0-9_-]{20,}', "Bearer ***REDACTED***"),
            (r'api_key["\']?\s*[:=]\s*["\'][^"\']+["\']', 'api_key="***REDACTED***"'),
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        return text
