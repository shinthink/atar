"""ATAR session search — search across saved sessions."""

from __future__ import annotations

from atar_core.session import Session, SessionManager


class SessionSearch:
    def __init__(self, manager: SessionManager | None = None) -> None:
        self.sessions = manager or SessionManager()

    def search(self, query: str, limit: int = 10) -> list[tuple[Session, list[str]]]:
        """Search sessions for query. Returns matching sessions with snippet lines."""
        results: list[tuple[Session, list[str]]] = []
        q = query.lower()
        for sess in self.sessions.list():
            snippets: list[str] = []
            for msg in sess.messages:
                if q in msg.content.lower():
                    snippet = msg.content[:200] + ("..." if len(msg.content) > 200 else "")
                    snippets.append(f"[{msg.role}] {snippet}")
            if snippets:
                results.append((sess, snippets[:3]))
            if len(results) >= limit:
                break
        return results

    def recent(self, n: int = 5) -> list[Session]:
        return self.sessions.list()[:n]


class MemoryEngine:
    """Simple key-value memory with persistence."""

    def __init__(self, path: str = ".atar/memory.json") -> None:
        import json
        import os
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._facts: dict[str, str] = {}
        if os.path.exists(path):
            with open(path) as f:
                self._facts = json.load(f)

    def save(self, key: str, value: str) -> None:
        self._facts[key] = value
        self._flush()

    def recall(self, key: str) -> str | None:
        return self._facts.get(key)

    def search(self, query: str) -> list[tuple[str, str]]:
        q = query.lower()
        return [(k, v) for k, v in self._facts.items() if q in k.lower() or q in v.lower()]

    def forget(self, key: str) -> bool:
        if key in self._facts:
            del self._facts[key]
            self._flush()
            return True
        return False

    def all(self) -> dict[str, str]:
        return dict(self._facts)

    def _flush(self) -> None:
        import json
        with open(self.path, "w") as f:
            json.dump(self._facts, f, indent=2, default=str)
