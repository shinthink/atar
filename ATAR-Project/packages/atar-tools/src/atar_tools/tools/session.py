"""ATAR session search tool — query past sessions via FTS5."""

from __future__ import annotations

from typing import Any

from atar_models.tools import ToolContext, ToolResult
from atar_storage.sqlite_store import SqliteStore

from atar_tools.registry import register


async def _session_search(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    query = args.get("query", "")
    limit = min(args.get("limit", 5), 20)

    try:
        store = SqliteStore()
        results = store.search(query, limit=limit) if query else store.list_all(limit=limit)

        if not results:
            return ToolResult(success=True, output="No matching sessions found.")

        lines = []
        for r in results:
            sid = r.get("session_id", "")[:12]
            title = r.get("title", "Untitled")
            snippet = r.get("snippet", "")
            count = r.get("message_count", "?")
            updated = r.get("updated_at", "")
            lines.append(f"[{sid}] {title} ({count} msgs) {updated}")
            if snippet:
                lines.append(f"    ...{snippet}...")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            metadata={"results": len(results), "query": query},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _session_resume(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    session_id = args.get("session_id", "")
    if not session_id:
        return ToolResult(success=False, error="session_id required")

    try:
        store = SqliteStore()
        data = store.load(session_id)
        if not data:
            return ToolResult(success=False, error=f"Session not found: {session_id[:12]}")

        msgs = data.get("messages", [])
        preview = "\n".join(
            f"[{m.get('role','?')}] {str(m.get('content',''))[:120]}" for m in msgs[-10:]
        )
        return ToolResult(
            success=True,
            output=f"Session: {data['title']}\n{len(msgs)} messages\n\n{preview}",
            metadata={"session_id": session_id, "messages": len(msgs)},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register("session_search", "Search past sessions via FTS5", _session_search, parameters={
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "limit": {"type": "integer", "description": "Max results (1-20)"},
    },
    "required": [],
})

register("session_resume", "Load a past session by ID", _session_resume, parameters={
    "type": "object",
    "properties": {
        "session_id": {"type": "string", "description": "Session ID to resume"},
    },
    "required": ["session_id"],
})
