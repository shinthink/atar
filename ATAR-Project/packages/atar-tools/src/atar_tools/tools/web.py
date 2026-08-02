"""ATAR web tools — HTTP fetch with text extraction."""

from __future__ import annotations

import re
from typing import Any

import httpx
from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _web_fetch(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    url = args.get("url", "")
    if not url:
        return ToolResult(success=False, error="url required")
    timeout = args.get("timeout", 15)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            resp = await client.get(url, follow_redirects=True, headers={
                "User-Agent": "ATAR/0.1 (web-research)"
            })
            resp.raise_for_status()

        text = _extract_text(resp.text)
        if len(text) > 30_000:
            text = text[:30_000] + "\n... [truncated]"

        return ToolResult(
            success=True,
            output=text,
            metadata={"url": url, "status": resp.status_code, "bytes": len(resp.text)},
        )
    except httpx.TimeoutException:
        return ToolResult(success=False, error=f"Timeout after {timeout}s")
    except httpx.HTTPStatusError as e:
        return ToolResult(success=False, error=f"HTTP {e.response.status_code}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def _extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    # Remove scripts, styles, head
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<head[^>]*>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Strip all tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    # Decode entities
    import html as html_mod
    text = html_mod.unescape(text)
    return text.strip()


register(
    "web_fetch",
    "Fetch and extract text from a URL",
    _web_fetch,
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "timeout": {"type": "integer", "description": "Timeout seconds"},
        },
        "required": ["url"],
    },
    max_output_chars=30_000,
    destructive=False,
)
