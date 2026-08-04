"""ATAR MCP client — connect to external MCP servers and register tools."""

from __future__ import annotations

import json
import subprocess
from typing import Any


class MCPClient:
    """Minimal MCP protocol client via stdio transport."""

    def __init__(self, command: str, args: list[str] | None = None) -> None:
        self.command = command
        self.args = args or []
        self._process: subprocess.Popen | None = None

    def start(self) -> bool:
        try:
            self._process = subprocess.Popen(
                [self.command] + self.args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                text=True, bufsize=1,
            )
            self._send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "atar", "version": "0.6.0"},
            }})
            resp = self._recv()
            return resp is not None and "result" in resp
        except Exception:
            return False

    def list_tools(self) -> list[dict]:
        self._send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        resp = self._recv()
        return resp.get("result", {}).get("tools", []) if resp else []

    def call_tool(self, name: str, arguments: dict) -> Any:
        self._send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
        resp = self._recv()
        return resp.get("result", {}) if resp else {}

    def _send(self, msg: dict) -> None:
        if self._process and self._process.stdin:
            self._process.stdin.write(json.dumps(msg) + "\n")
            self._process.stdin.flush()

    def _recv(self) -> dict | None:
        if self._process and self._process.stdout:
            line = self._process.stdout.readline()
            return json.loads(line) if line.strip() else None
        return None

    def close(self) -> None:
        if self._process:
            self._process.terminate()
