"""ATAR API server with streaming SSE for Ink frontend.
Optional — requires `pip install fastapi uvicorn`.
"""

from __future__ import annotations

import asyncio
import json
import sys


def start_server(host: str = "127.0.0.1", port: int = 8420):
    """Start the ATAR API server. Requires fastapi+uvicorn installed."""
    try:
        import uvicorn
        from fastapi import FastAPI
        from fastapi.responses import StreamingResponse
        from pydantic import BaseModel
    except ImportError:
        print("fastapi not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
        return

    app = FastAPI(title="ATAR API")

    class ChatRequest(BaseModel):
        message: str

    async def _stream_agent(message: str):
        """Stream agent response via SSE (Server-Sent Events)."""
        from atar_core.agent import Agent, StreamCallbacks
        from atar_core.provider_registry import get_provider

        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def on_delta(text: str) -> None:
            await queue.put(json.dumps({"type": "delta", "text": text}))

        provider = get_provider()
        agent = Agent(provider=provider, max_turns=10, interactive=False)

        async def run_agent():
            try:
                await agent.run(message, StreamCallbacks(on_delta=on_delta))
                await queue.put(json.dumps({"type": "done"}))
            except Exception as e:
                await queue.put(json.dumps({"type": "error", "error": str(e)}))
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_agent())

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield f"data: {chunk}\n\n"

        await task

    @app.post("/chat")
    async def chat(req: ChatRequest):
        return StreamingResponse(
            _stream_agent(req.message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/health")
    async def health():
        from atar_core.provider_registry import get_provider
        try:
            p = get_provider()
            return {"status": "ok", "provider": p.model or "loaded"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_server()
