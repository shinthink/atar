"""ATAR MCP connector — JSON-RPC over stdio for MCP servers.

Per blueprint Section 21. Connects to MCP-compatible servers via subprocess.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any


class MCPConnector:
    """Connect to MCP servers via stdio JSON-RPC."""

    def __init__(self, command: str = "", args: list[str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self._proc: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def connect(self) -> bool:
        if not self.command:
            return False
        try:
            self._proc = await asyncio.create_subprocess_exec(
                self.command, *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            # Initialize
            result = await self._rpc("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "atar", "version": "0.1"},
            })
            return result is not None
        except Exception:
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self._rpc("tools/list", {})
        return result.get("tools", []) if result else []

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        result = await self._rpc("tools/call", {"name": name, "arguments": args})
        return result or {"error": "Tool call failed"}

    async def disconnect(self) -> None:
        if self._proc and self._proc.stdin:
            self._proc.stdin.close()
            await self._proc.wait()
            self._proc = None

    async def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if not self._proc or not self._proc.stdin or not self._proc.stdout:
            return None
        self._request_id += 1
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }) + "\n"
        try:
            self._proc.stdin.write(req.encode())
            await self._proc.stdin.drain()
            line = await asyncio.wait_for(self._proc.stdout.readline(), timeout=10)
            if line:
                data = json.loads(line.decode())
                if "result" in data:
                    return data["result"]
        except Exception:
            pass
        return None
