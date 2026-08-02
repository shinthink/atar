"""ATAR SQLite session storage — models + async repository. Per ADR-003."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    title = Column(String, default="")
    messages_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class SqliteSessionStore:
    """SQLite-backed session repository."""

    def __init__(self, db_path: str = ".atar/sessions.db") -> None:
        import os
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        # Create FTS5 index (simpler approach)
        with self.engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5("
                "session_id, title, messages)"
            ))
            conn.commit()

    def save(self, session_id: str, title: str, messages: list) -> None:
        with self.Session() as sess:
            model = sess.get(SessionModel, session_id)
            if not model:
                model = SessionModel(session_id=session_id)
                sess.add(model)
            model.title = title
            model.messages_json = json.dumps([
                {
                    "role": m.role,
                    "content": m.content,
                    "tool_calls": getattr(m, "tool_calls", None),
                    "tool_call_id": getattr(m, "tool_call_id", None),
                }
                for m in messages if hasattr(m, "role")
            ])
            model.updated_at = datetime.now(UTC)
            sess.commit()
        # Sync to FTS5
        with self.Session() as sess2:
            from sqlalchemy import text
            msg_text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
            sess2.execute(text(
                "INSERT OR REPLACE INTO sessions_fts(rowid, session_id, title, messages) "
                "VALUES ((SELECT rowid FROM sessions WHERE session_id=:sid), :sid, :title, :msg)"
            ), {"sid": session_id, "title": title, "msg": msg_text})
            sess2.commit()

    def load(self, session_id: str) -> dict | None:
        with self.Session() as sess:
            model = sess.get(SessionModel, session_id)
            if not model:
                return None
            return {
                "session_id": model.session_id,
                "title": model.title,
                "messages": json.loads(model.messages_json),
                "created_at": model.created_at.isoformat() if model.created_at else "",
                "updated_at": model.updated_at.isoformat() if model.updated_at else "",
            }

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """FTS5 full-text search across sessions."""
        with self.Session() as sess:
            try:
                from sqlalchemy import text
                rows = sess.execute(
                    text(
                        "SELECT session_id, title, snippet(sessions_fts, 2, '<b>', '</b>', '...', 40) "
                        "FROM sessions_fts WHERE sessions_fts MATCH :q LIMIT :l"
                    ),
                    {"q": query, "l": limit},
                ).fetchall()
                return [{"session_id": r[0], "title": r[1], "snippet": r[2]} for r in rows]
            except Exception:
                return []

    def list_all(self, limit: int = 20) -> list[dict]:
        with self.Session() as sess:
            models = sess.query(SessionModel).order_by(SessionModel.updated_at.desc()).limit(limit).all()
            return [{
                "session_id": m.session_id,
                "title": m.title,
                "message_count": len(json.loads(m.messages_json)),
                "updated_at": m.updated_at.isoformat() if m.updated_at else "",
            } for m in models]
