"""ATAR web tools — HTTP fetch with SSRF protection and text extraction."""

from __future__ import annotations

import ipaddress
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register

# SSRF-blocked IP ranges
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # private A
    ipaddress.ip_network("172.16.0.0/12"),     # private B
    ipaddress.ip_network("192.168.0.0/16"),    # private C
    ipaddress.ip_network("169.254.0.0/16"),    # link-local / cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),         # current network
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Check if URL is safe to fetch. Returns (ok, reason)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "invalid URL"

    if parsed.scheme not in ("http", "https"):
        return False, f"scheme not allowed: {parsed.scheme}"

    hostname = parsed.hostname
    if not hostname:
        return False, "no hostname"

    try:
        addr = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if addr in net:
                return False, f"IP blocked: {hostname} ({net})"
    except ValueError:
        pass  # not an IP, DNS will resolve

    return True, ""


async def _web_fetch(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    url = args.get("url", "")
    if not url:
        return ToolResult(success=False, error="url required")

    ok, reason = _is_safe_url(url)
    if not ok:
        return ToolResult(success=False, error=f"SSRF blocked: {reason}")

    timeout = min(args.get("timeout", 15), 60)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            resp = await client.get(url, follow_redirects=True, headers={
                "User-Agent": "ATAR/0.7 (web-research)"
            })

            # Revalidate redirect target
            final_url = str(resp.url)
            if final_url != url:
                ok2, reason2 = _is_safe_url(final_url)
                if not ok2:
                    return ToolResult(success=False, error=f"SSRF blocked on redirect: {reason2}")

            resp.raise_for_status()

        text = _extract_text(resp.text)
        if len(text) > 30_000:
            text = text[:30_000] + "\n... [truncated]"

        return ToolResult(
            success=True,
            output=text,
            metadata={"url": url, "final_url": final_url if final_url != url else None, "status": resp.status_code, "bytes": len(resp.text)},
        )
    except httpx.TimeoutException:
        return ToolResult(success=False, error=f"Timeout after {timeout}s")
    except httpx.HTTPStatusError as e:
        return ToolResult(success=False, error=f"HTTP {e.response.status_code}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def _extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<head[^>]*>.*?</head>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
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
            "timeout": {"type": "integer", "description": "Timeout seconds (max 60)"},
        },
        "required": ["url"],
    },
    max_output_chars=30_000,
    destructive=False,
)
