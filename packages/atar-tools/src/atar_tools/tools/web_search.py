"""ATAR web_search tool — DuckDuckGo HTML search, no API key needed."""

from __future__ import annotations

from typing import Any

import httpx
from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register


async def _web_search(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Search the web using DuckDuckGo HTML endpoint."""
    query = args.get("query", "")
    if not query:
        return ToolResult(success=False, error="query required")

    limit = min(args.get("limit", 5), 10)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "ATAR/1.0 (web-research-agent)"},
                follow_redirects=True,
            )
            resp.raise_for_status()

        # Parse DuckDuckGo HTML results
        results = _parse_ddg_html(resp.text, limit)
        if not results:
            return ToolResult(success=True, output="No results found.", metadata={"query": query, "count": 0})

        output = ""
        for i, r in enumerate(results):
            output += f"[{i+1}] {r['title']}\n    URL: {r['url']}\n    {r['snippet']}\n\n"

        return ToolResult(
            success=True,
            output=output.strip(),
            metadata={"query": query, "count": len(results), "results": results},
        )
    except httpx.TimeoutException:
        return ToolResult(success=False, error="Search timeout")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def _parse_ddg_html(html: str, limit: int) -> list[dict[str, str]]:
    """Extract results from DuckDuckGo HTML page."""
    import re
    results = []

    # Find result blocks: <a class="result__a" href="URL">TITLE</a>
    # followed by <a class="result__snippet">SNIPPET</a>
    links = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
    snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    for i, (url, title) in enumerate(links[:limit]):
        title_clean = _strip_html(title).strip()[:200]
        url_clean = url.strip()
        snippet = _strip_html(snippets[i]).strip()[:300] if i < len(snippets) else ""
        if url_clean and title_clean:
            results.append({"title": title_clean, "url": url_clean, "snippet": snippet})

    return results


def _strip_html(text: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", text).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')


register(
    "web_search",
    "Search the web for information using DuckDuckGo",
    _web_search,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (1-10, default 5)"},
        },
        "required": ["query"],
    },
    max_output_chars=5000,
    destructive=False,
)
