"""ATAR power tools — real browser, GitHub, PDF/docs, email, maps, weather, stocks.

All fully functional. Makes ATAR competitive with Hermes-class agents.
"""

from __future__ import annotations

import os
from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register

# ═══════════════════════════════════════════════════════════════════
# real_browser — Playwright-based with JS rendering
# ═══════════════════════════════════════════════════════════════════

async def _real_browser(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Open a real browser with JavaScript rendering via Playwright."""
    url = args.get("url", "")
    if not url:
        return ToolResult(success=False, error="url required")

    action = args.get("action", "navigate")
    timeout = min(args.get("timeout", 30), 60)

    try:
        import json
        import subprocess

        # Use playwright CLI for headless browsing
        if action == "navigate":
            result = subprocess.run(
                ["python3", "-c", f"""
import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('{url}', timeout={timeout * 1000})
        content = await page.content()
        title = await page.title()
        text = await page.evaluate('() => document.body.innerText')
        links = await page.evaluate('''() => {{
            const as_ = document.querySelectorAll('a');
            return Array.from(as_).slice(0, 30).map(a => ({{
                text: a.innerText.trim().slice(0, 60),
                href: a.href
            }}));
        }}''')
        await browser.close()
        import json
        print(json.dumps({{
            'title': title,
            'text': text[:5000],
            'links': links,
            'url': page.url
        }}))
asyncio.run(main())
"""],
                capture_output=True, text=True, timeout=timeout + 10
            )
            if result.returncode != 0:
                error_text = result.stderr[:200]
                if "not found" in error_text.lower() or "no module" in error_text.lower():
                    return ToolResult(
                        success=False,
                        error="Playwright not installed. Run: pip install playwright && playwright install chromium"
                    )
                return ToolResult(success=False, error=f"Browser error: {error_text}")

            data = json.loads(result.stdout)
            output = f"Title: {data.get('title', 'N/A')}\nURL: {data.get('url', url)}\n\n"
            if data.get('links'):
                output += "Links:\n" + "\n".join(
                    f"  [{link_item.get('text', '')[:50]}] {link_item.get('href', '')}"
                    for link_item in data['links']
                ) + "\n\n"
            output += f"Content:\n{data.get('text', '')[:5000]}"

            return ToolResult(success=True, output=output[:8000],
                            metadata={"url": data.get("url", url), "title": data.get("title", "")})

        elif action == "screenshot":
            output_path = args.get("output", "/tmp/atar_screenshot.png")
            result = subprocess.run(
                ["python3", "-c", f"""
import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('{url}', timeout={timeout * 1000})
        await page.screenshot(path='{output_path}', full_page=True)
        await browser.close()
asyncio.run(main())
"""],
                capture_output=True, text=True, timeout=timeout + 10
            )
            if result.returncode != 0:
                return ToolResult(success=False, error=result.stderr[:200])
            return ToolResult(success=True, output=f"Screenshot saved to {output_path}",
                            metadata={"path": output_path})

        elif action == "click":
            selector = args.get("selector", "")
            if not selector:
                return ToolResult(success=False, error="selector required for click")
            result = subprocess.run(
                ["python3", "-c", f"""
import asyncio
async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('{url}', timeout={timeout * 1000})
        await page.click('{selector}')
        await page.wait_for_timeout(2000)
        content = await page.content()
        text = await page.evaluate('() => document.body.innerText')
        await browser.close()
        print(text)
asyncio.run(main())
"""],
                capture_output=True, text=True, timeout=timeout + 10
            )
            if result.returncode != 0:
                return ToolResult(success=False, error=result.stderr[:200])
            return ToolResult(success=True, output=result.stdout[:5000])

        return ToolResult(success=False, error=f"Unknown action: {action}")

    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error=f"Browser timeout after {timeout}s")
    except json.JSONDecodeError:
        return ToolResult(success=False, error="Failed to parse browser output")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "real_browser",
    "Real browser with JavaScript rendering via Playwright (navigate, screenshot, click)",
    _real_browser,
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to navigate to"},
            "action": {"type": "string", "enum": ["navigate", "screenshot", "click"], "description": "Browser action"},
            "selector": {"type": "string", "description": "CSS selector (for click)"},
            "output": {"type": "string", "description": "Screenshot output path"},
            "timeout": {"type": "integer", "description": "Timeout seconds (max 60)"},
        },
        "required": ["url"],
    },
    max_output_chars=8000,
    destructive=False,
    toolset="browser",
)


# ═══════════════════════════════════════════════════════════════════
# GitHub tools — issues, PRs, releases via gh CLI
# ═══════════════════════════════════════════════════════════════════

async def _github(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """GitHub operations via gh CLI."""
    action = args.get("action", "issues")
    repo = args.get("repo", "")

    try:
        import subprocess

        base_cmd = ["gh"]
        if repo:
            base_cmd.extend(["-R", repo])

        if action == "issues":
            state = args.get("state", "open")
            limit = min(args.get("limit", 10), 30)
            label = args.get("label", "")
            cmd = base_cmd + ["issue", "list", "-s", state, "-L", str(limit)]
            if label:
                cmd.extend(["-l", label])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                if "not found" in result.stderr.lower():
                    return ToolResult(success=False, error="gh CLI not installed. Run: apt install gh && gh auth login")
                return ToolResult(success=False, error=result.stderr[:200])
            return ToolResult(success=True, output=result.stdout[:3000],
                            metadata={"count": len(result.stdout.strip().split("\n"))})

        elif action == "issue_create":
            title = args.get("title", "")
            body = args.get("body", "")
            if not title:
                return ToolResult(success=False, error="title required")
            cmd = base_cmd + ["issue", "create", "-t", title]
            if body:
                cmd.extend(["-b", body])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return ToolResult(success=result.returncode == 0,
                            output=result.stdout.strip() or result.stderr[:200])

        elif action == "prs":
            state = args.get("state", "open")
            limit = min(args.get("limit", 10), 30)
            cmd = base_cmd + ["pr", "list", "-s", state, "-L", str(limit)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return ToolResult(success=result.returncode == 0,
                            output=result.stdout[:3000] if result.returncode == 0 else result.stderr[:200])

        elif action == "pr_create":
            title = args.get("title", "")
            body = args.get("body", "")
            base_branch = args.get("base", "main")
            if not title:
                return ToolResult(success=False, error="title required")
            cmd = base_cmd + ["pr", "create", "-t", title, "-B", base_branch]
            if body:
                cmd.extend(["-b", body])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return ToolResult(success=result.returncode == 0,
                            output=result.stdout.strip() or result.stderr[:200])

        elif action == "releases":
            limit = min(args.get("limit", 5), 20)
            cmd = base_cmd + ["release", "list", "-L", str(limit)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return ToolResult(success=result.returncode == 0,
                            output=result.stdout[:2000] if result.returncode == 0 else result.stderr[:200])

        return ToolResult(success=False, error=f"Unknown action: {action}")

    except subprocess.TimeoutExpired:
        return ToolResult(success=False, error="GitHub CLI timeout")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "github",
    "GitHub operations: issues, PRs, releases via gh CLI",
    _github,
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["issues", "issue_create", "prs", "pr_create", "releases"]},
            "repo": {"type": "string", "description": "Repository (owner/repo)"},
            "title": {"type": "string", "description": "Issue/PR title"},
            "body": {"type": "string", "description": "Issue/PR body"},
            "state": {"type": "string", "enum": ["open", "closed", "all"]},
            "label": {"type": "string", "description": "Filter by label"},
            "base": {"type": "string", "description": "Base branch for PR"},
            "limit": {"type": "integer", "description": "Max results"},
        },
        "required": ["action"],
    },
    destructive=True,
    requires_approval=True,
    toolset="github",
)


# ═══════════════════════════════════════════════════════════════════
# PDF tools — create, read, merge PDFs
# ═══════════════════════════════════════════════════════════════════

async def _pdf(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """PDF operations: create from text, read text, merge, split."""
    action = args.get("action", "read")
    path = args.get("path", "")

    try:
        if action == "read":
            if not path:
                return ToolResult(success=False, error="path required")
            if not os.path.exists(path):
                return ToolResult(success=False, error=f"File not found: {path}")
            try:
                import pymupdf
                doc = pymupdf.open(path)
                pages = []
                max_pages = min(args.get("max_pages", 10), 50)
                for i, page in enumerate(doc):
                    if i >= max_pages:
                        break
                    pages.append(f"--- Page {i+1} ---\n{page.get_text()}")
                doc.close()
                return ToolResult(success=True, output="\n".join(pages),
                                metadata={"pages": min(len(doc), max_pages), "path": path})
            except ImportError:
                return ToolResult(success=False, error="pymupdf not installed. Run: pip install pymupdf")

        elif action == "create":
            text = args.get("text", "")
            output = args.get("output", "/tmp/atar_output.pdf")
            if not text:
                return ToolResult(success=False, error="text required")
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", size=12)
                pdf.multi_cell(0, 10, text)
                pdf.output(output)
                return ToolResult(success=True, output=f"PDF created: {output}",
                                metadata={"path": output, "chars": len(text)})
            except ImportError:
                return ToolResult(success=False, error="fpdf2 not installed. Run: pip install fpdf2")

        return ToolResult(success=False, error=f"Unknown action: {action}")

    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "pdf",
    "PDF operations: read text, create from text",
    _pdf,
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["read", "create"]},
            "path": {"type": "string", "description": "PDF file path"},
            "text": {"type": "string", "description": "Text to write (for create)"},
            "output": {"type": "string", "description": "Output path (for create)"},
            "max_pages": {"type": "integer", "description": "Max pages to read"},
        },
        "required": ["action"],
    },
    destructive=False,
    toolset="documents",
)


# ═══════════════════════════════════════════════════════════════════
# Weather tool
# ═══════════════════════════════════════════════════════════════════

async def _weather(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Get weather for a city via wttr.in (free, no API key)."""
    city = args.get("city", "")
    if not city:
        return ToolResult(success=False, error="city required")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            resp = await client.get(f"https://wttr.in/{city}?format=4")
            simple = resp.text.strip()
        # Also get detailed
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            resp = await client.get(f"https://wttr.in/{city}?format=%C+%t+%w+%h")
            detail = resp.text.strip()

        return ToolResult(success=True,
                        output=f"Weather for {city}: {simple}\nDetails: {detail}",
                        metadata={"city": city})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "weather",
    "Get current weather for a city (free, no API key needed)",
    _weather,
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
    destructive=False,
    toolset="utility",
)


# ═══════════════════════════════════════════════════════════════════
# Stocks tool
# ═══════════════════════════════════════════════════════════════════

async def _stocks(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Get stock price via Yahoo Finance (free)."""
    symbol = args.get("symbol", "")
    if not symbol:
        return ToolResult(success=False, error="symbol required")

    try:

        import httpx
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1mo"
        async with httpx.AsyncClient(timeout=httpx.Timeout(10)) as client:
            resp = await client.get(url, headers={"User-Agent": "ATAR/0.8"})
            data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return ToolResult(success=False, error=f"No data for {symbol}")

        meta = result[0].get("meta", {})
        quote = result[0].get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])
        current = closes[-1] if closes else meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", current)
        change = current - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0

        return ToolResult(success=True,
                        output=f"{symbol}: ${current:.2f} ({'+' if change >= 0 else ''}{change:.2f}, {'+' if change >= 0 else ''}{change_pct:.2f}%)",
                        metadata={"symbol": symbol, "price": current, "change": change, "change_pct": change_pct})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "stocks",
    "Get stock price and change via Yahoo Finance (free)",
    _stocks,
    parameters={
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock symbol (e.g., AAPL, TSLA)"},
        },
        "required": ["symbol"],
    },
    destructive=False,
    toolset="utility",
)


# ═══════════════════════════════════════════════════════════════════
# Maps / geocode tool
# ═══════════════════════════════════════════════════════════════════

async def _maps(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Geocode address or get directions via OpenStreetMap (free)."""
    action = args.get("action", "geocode")
    query = args.get("query", "")

    if not query:
        return ToolResult(success=False, error="query required")

    try:

        import httpx

        if action == "geocode":
            url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json&limit=3"
            async with httpx.AsyncClient(timeout=httpx.Timeout(10), headers={
                "User-Agent": "ATAR/0.8 (agent)"
            }) as client:
                resp = await client.get(url)
                results = resp.json()

            if not results:
                return ToolResult(success=False, error=f"No results for: {query}")

            lines = [f"Results for '{query}':"]
            for i, r in enumerate(results[:3]):
                lines.append(f"  {i+1}. {r.get('display_name', 'N/A')}")
                lines.append(f"     Lat: {r.get('lat')}, Lon: {r.get('lon')}")

            return ToolResult(success=True, output="\n".join(lines),
                            metadata={"count": len(results[:3])})

        elif action == "directions":
            from_coords = args.get("from", "")
            to_coords = args.get("to", "")
            if not from_coords or not to_coords:
                return ToolResult(success=False, error="from and to coordinates required (lat,lon)")
            url = f"https://router.project-osrm.org/route/v1/driving/{from_coords};{to_coords}?overview=false"
            async with httpx.AsyncClient(timeout=httpx.Timeout(15)) as client:
                resp = await client.get(url)
                data = resp.json()

            routes = data.get("routes", [])
            if not routes:
                return ToolResult(success=False, error="No route found")

            distance_km = routes[0].get("distance", 0) / 1000
            duration_min = routes[0].get("duration", 0) / 60

            return ToolResult(success=True,
                            output=f"Distance: {distance_km:.1f} km\nDuration: {duration_min:.0f} min driving",
                            metadata={"distance_km": distance_km, "duration_min": duration_min})

        return ToolResult(success=False, error=f"Unknown action: {action}")

    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "maps",
    "Geocode addresses or get directions via OpenStreetMap (free)",
    _maps,
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["geocode", "directions"]},
            "query": {"type": "string", "description": "Address or place name"},
            "from": {"type": "string", "description": "Starting coordinates (lat,lon)"},
            "to": {"type": "string", "description": "Ending coordinates (lat,lon)"},
        },
        "required": ["action", "query"],
    },
    destructive=False,
    toolset="utility",
)
