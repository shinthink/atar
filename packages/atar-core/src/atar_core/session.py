"""ATAR session manager — persistent chat sessions with context stack.

Per blueprint Section 13 (Storage) and Section 14 (Prompt/Context Engine).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from atar_models.requests import Message

if TYPE_CHECKING:
    pass


class Session:
    """In-memory session that syncs to database."""

    def __init__(self, session_id: str, title: str = "") -> None:
        self.session_id = session_id
        self.title = title or f"Session-{session_id[:8]}"
        self.messages: list[Message] = []
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.now(UTC)

    def to_model(self) -> dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "messages_json": _serialize(self.messages),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_model(cls, data: dict) -> Session:
        s = cls(session_id=data["session_id"], title=data.get("title", ""))
        s.messages = _deserialize(data.get("messages_json", "[]"))
        s.created_at = datetime.fromisoformat(data.get("created_at", ""))
        s.updated_at = datetime.fromisoformat(data.get("updated_at", ""))
        return s


class SessionManager:
    """Manages session lifecycle: create, load, save, list."""

    def __init__(self, storage_path: str = ".atar") -> None:
        self.storage_path = storage_path
        self._store_file = os.path.join(storage_path, "sessions.json")
        self._active: Session | None = None
        self._registry: dict[str, Session] = {}
        self._load_store()

    @property
    def active(self) -> Session | None:
        return self._active

    def new(self, title: str = "") -> Session:
        import uuid
        sid = uuid.uuid4().hex[:12]
        s = Session(session_id=sid, title=title)
        self._registry[sid] = s
        self._active = s
        self._flush()
        return s

    def load(self, session_id: str) -> Session:
        s = self._registry.get(session_id)
        if s:
            self._active = s
            return s
        s = Session(session_id=session_id)
        self._registry[session_id] = s
        self._active = s
        return s

    def list(self) -> list[Session]:
        return sorted(self._registry.values(), key=lambda s: s.updated_at, reverse=True)

    def save(self) -> None:
        if self._active:
            self._registry[self._active.session_id] = self._active
            self._flush()

    def delete(self, session_id: str) -> None:
        self._registry.pop(session_id, None)
        if self._active and self._active.session_id == session_id:
            self._active = None
        self._flush()

    def _flush(self) -> None:
        import os as _os
        _os.makedirs(self.storage_path, exist_ok=True)
        data = {sid: s.to_model() for sid, s in self._registry.items()}
        with open(self._store_file, "w") as f:
            import json
            json.dump(data, f, default=str, indent=2)
        # Also save to SQLite
        from atar_storage.sqlite_store import SqliteSessionStore
        try:
            store = SqliteSessionStore()
            for sid, s in self._registry.items():
                store.save(sid, s.title, s.messages)
        except Exception:
            pass  # SQLite is best-effort for now

    def _load_store(self) -> None:
        import os as _os
        if not _os.path.exists(self._store_file):
            return
        with open(self._store_file) as f:
            import json
            data = json.load(f)
        for sid, raw in data.items():
            self._registry[sid] = Session.from_model(raw)


def _serialize(messages: list[Message]) -> str:
    import json
    return json.dumps([{"role": m.role, "content": m.content} for m in messages])


def _deserialize(data: str) -> list[Message]:
    import json
    items = json.loads(data) if data else []
    return [Message(role=item["role"], content=item["content"]) for item in items]
