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
    except ImportError:
        print("fastapi not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
        return

    app = FastAPI(title="ATAR API")

    # CORS for Ink frontend
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    async def _stream_agent(message: str):
        """Stream agent response via SSE (Server-Sent Events)."""
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        try:
            from atar_core.agent import Agent, StreamCallbacks
            from atar_core.provider_registry import list_available
            providers = list_available()
            if not providers:
                await queue.put(json.dumps({"type": "delta", "text": "No AI provider configured.\n\n"}))
                await queue.put(json.dumps({"type": "delta", "text": "Run: uv run atar setup\n"}))
                await queue.put(json.dumps({"type": "done"}))
                await queue.put(None)
                # Stream and exit
                while True:
                    chunk = await queue.get()
                    if chunk is None:
                        break
                    yield f"data: {chunk}\n\n"
                return
            provider = providers[0]
        except Exception as e:
            await queue.put(json.dumps({"type": "error", "error": f"Provider init failed: {e}"}))
            await queue.put(None)
            # Stream error and exit
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield f"data: {chunk}\n\n"
            return

        async def on_delta(text: str) -> None:
            await queue.put(json.dumps({"type": "delta", "text": text}))

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
    async def chat(request_body: dict):
        """Streaming chat endpoint — accepts JSON {message: str}."""
        message = request_body.get("message", "") if request_body else ""
        if not message:
            return {"error": "message is required"}
        return StreamingResponse(
            _stream_agent(message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/health")
    async def health():
        from atar_core.provider_registry import list_available
        try:
            providers = list_available()
            return {"status": "ok", "providers": len(providers)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @app.on_event("startup")
    async def startup():
        print(f"ATAR API + Web UI → http://{host}:{port}")

    @app.get("/")
    async def index():
        # Serve the web UI HTML
        import os
        html_path = os.path.join(os.path.dirname(__file__), "web_ui.html")
        if os.path.exists(html_path):
            from fastapi.responses import FileResponse
            return FileResponse(html_path)
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<h1>ATAR Web UI</h1><p>web_ui.html not found</p>")

    uv_config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(uv_config)
    server.run()


if __name__ == "__main__":
    start_server()
