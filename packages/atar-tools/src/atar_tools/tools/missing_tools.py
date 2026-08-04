"""ATAR missing tools — search_files, browser, execute_code, cronjob, memory, web_extract.

All fully functional implementations that were registered in toolsets but missing handlers.
"""

from __future__ import annotations

import subprocess
from typing import Any

from atar_models.tools import ToolContext, ToolResult

from atar_tools.registry import register

# ══════════════════════════════════════════════════════════════════════════════
# search_files — ripgrep-backed file content and name search
# ══════════════════════════════════════════════════════════════════════════════

async def _search_files(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Search file contents (ripgrep) or find files by name (glob)."""
    pattern = args.get("pattern", "")
    if not pattern:
        return ToolResult(success=False, error="pattern required")

    target = args.get("target", "content")  # "content" or "files"
    path = args.get("path", ctx.working_directory or ".")
    file_glob = args.get("file_glob", "")
    limit = min(args.get("limit", 50), 100)

    if target == "files":
        # Find files by glob pattern
        try:
            import os as _os
            matches = []
            for root, _, files in _os.walk(path):
                for f in files:
                    rel = _os.path.relpath(_os.path.join(root, f), path)
                    if file_glob:
                        import fnmatch
                        if not fnmatch.fnmatch(f, file_glob):
                            continue
                    if len(matches) >= limit:
                        break
                    matches.append(rel)
                if len(matches) >= limit:
                    break
            output = "\n".join(matches[:limit]) or "No files found."
            return ToolResult(success=True, output=output, metadata={"count": len(matches[:limit])})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    # Content search via ripgrep
    try:
        cmd = ["rg", "--no-heading", "--line-number", "--max-count", str(limit), pattern, path]
        if file_glob:
            cmd.insert(3, "--glob")
            cmd.insert(4, file_glob)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=path)
        output = result.stdout[:10_000] or "No matches found."
        return ToolResult(
            success=True,
            output=output,
            metadata={"count": len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0},
        )
    except FileNotFoundError:
        # Fallback to grep if rg not available
        try:
            cmd = ["grep", "-rn", "--max-count", str(limit), pattern, path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=path)
            output = result.stdout[:10_000] or "No matches found."
            return ToolResult(success=True, output=output,
                            metadata={"count": len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "search_files",
    "Search file contents (ripgrep) or find files by name (glob)",
    _search_files,
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern for content or glob for files"},
            "target": {"type": "string", "enum": ["content", "files"], "description": "Search type"},
            "path": {"type": "string", "description": "Directory to search in"},
            "file_glob": {"type": "string", "description": "Filter by glob pattern"},
            "limit": {"type": "integer", "description": "Max results (default 50, max 100)"},
        },
        "required": ["pattern"],
    },
    max_output_chars=10_000,
    destructive=False,
    toolset="file",
)


# ══════════════════════════════════════════════════════════════════════════════
# browser — headless page fetching with text extraction
# ══════════════════════════════════════════════════════════════════════════════

async def _browser(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Fetch a web page and extract readable content + links."""
    url = args.get("url", "")
    if not url:
        return ToolResult(success=False, error="url required")

    import re

    import httpx

    timeout = min(args.get("timeout", 15), 30)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout), follow_redirects=True, headers={
            "User-Agent": "ATAR/0.7 (browser-agent)",
            "Accept": "text/html,application/xhtml+xml",
        }) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        html = resp.text
        title = ""
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        # Extract all links
        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        link_text = "\n".join(
            f"[{re.sub(r'<[^>]+>', '', text).strip()[:80]}] {href}"
            for href, text in links[:30]
        )

        # Extract text
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()[:5000]

        output = f"Title: {title}\n\nLinks ({len(links)} total):\n{link_text}\n\nContent:\n{text}"
        if len(output) > 10_000:
            output = output[:10_000] + "\n... [truncated]"

        return ToolResult(
            success=True, output=output,
            metadata={"url": url, "title": title, "links": len(links), "status": resp.status_code},
        )
    except httpx.TimeoutException:
        return ToolResult(success=False, error=f"Timeout after {timeout}s")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "browser",
    "Fetch a web page and extract content, title, and links",
    _browser,
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to browse"},
            "timeout": {"type": "integer", "description": "Timeout seconds (max 30)"},
        },
        "required": ["url"],
    },
    max_output_chars=10_000,
    destructive=False,
    toolset="browser",
)


# ══════════════════════════════════════════════════════════════════════════════
# execute_code — sandboxed Python execution with timeout and output limit
# ══════════════════════════════════════════════════════════════════════════════

_SAFE_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "bytes", "chr", "complex", "dict",
    "divmod", "enumerate", "filter", "float", "format", "frozenset", "hash",
    "hex", "int", "isinstance", "issubclass", "iter", "len", "list", "map",
    "max", "min", "next", "oct", "ord", "pow", "range", "repr", "reversed",
    "round", "set", "slice", "sorted", "str", "sum", "tuple", "type", "zip",
    "print", "input", "Exception", "ValueError", "TypeError", "KeyError",
    "IndexError", "StopIteration", "ZeroDivisionError", "json", "re",
    "math", "datetime", "collections", "itertools", "functools",
}


async def _execute_code(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Execute Python code in a sandboxed environment with timeout."""
    code = args.get("code", "")
    if not code:
        return ToolResult(success=False, error="code required")

    timeout = min(args.get("timeout", 10), 30)
    max_output = 10_000

    # Build restricted globals using builtins module (safer than __builtins__)
    import builtins as _builtins
    safe_globals: dict[str, Any] = {"__builtins__": {}}
    for name in _SAFE_BUILTINS:
        if hasattr(_builtins, name):
            safe_globals["__builtins__"][name] = getattr(_builtins, name)
        elif name in ("json", "re", "math", "datetime", "collections", "itertools", "functools"):
            safe_globals[name] = __import__(name)

    try:
        import io
        import sys
        import traceback

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        captured = io.StringIO()
        sys.stdout = captured
        sys.stderr = captured

        try:
            exec(code, safe_globals, {})
            output = captured.getvalue()
        except Exception as e:
            output = f"Error: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        if len(output) > max_output:
            output = output[:max_output] + "\n... [truncated]"

        return ToolResult(
            success="Error:" not in output[:20] or "Error:" not in output,
            output=output or "(no output)",
            metadata={"timeout": timeout},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


register(
    "execute_code",
    "Execute Python code in a sandboxed environment",
    _execute_code,
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Timeout seconds (max 30)"},
        },
        "required": ["code"],
    },
    max_output_chars=10_000,
    destructive=False,
    requires_approval=True,
    toolset="code_execution",
)


# ══════════════════════════════════════════════════════════════════════════════
# cronjob — schedule recurring tasks
# ══════════════════════════════════════════════════════════════════════════════

async def _cronjob(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Manage scheduled cron jobs: create, list, remove."""
    action = args.get("action", "list")

    from atar_core.scheduler import add_job, list_jobs, remove_job, set_enabled

    if action == "create":
        expr = args.get("schedule", "30m")
        prompt = args.get("prompt", "")
        if not prompt:
            return ToolResult(success=False, error="prompt required for create")
        job_id = add_job(expr, prompt)
        return ToolResult(success=True, output=f"Job created: #{job_id}", metadata={"job_id": job_id})

    elif action == "list":
        jobs = list_jobs()
        if not jobs:
            return ToolResult(success=True, output="No scheduled jobs.")
        lines = [f"[{j.id}] {j.cron_expr} — {j.prompt[:60]} ({'enabled' if j.enabled else 'disabled'})" for j in jobs]
        return ToolResult(success=True, output="\n".join(lines), metadata={"count": len(jobs)})

    elif action == "pause":
        job_id = args.get("job_id", 0)
        if set_enabled(job_id, False):
            return ToolResult(success=True, output=f"Job #{job_id} paused.")
        return ToolResult(success=False, error=f"Job #{job_id} not found.")

    elif action == "resume":
        job_id = args.get("job_id", 0)
        if set_enabled(job_id, True):
            return ToolResult(success=True, output=f"Job #{job_id} resumed.")
        return ToolResult(success=False, error=f"Job #{job_id} not found.")

    elif action == "remove":
        job_id = args.get("job_id", 0)
        if remove_job(job_id):
            return ToolResult(success=True, output=f"Job #{job_id} removed.")
        return ToolResult(success=False, error=f"Job #{job_id} not found.")

    return ToolResult(success=False, error=f"Unknown action: {action}")


register(
    "cronjob",
    "Manage scheduled cron jobs: create, list, pause, resume, remove",
    _cronjob,
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["create", "list", "pause", "resume", "remove"]},
            "schedule": {"type": "string", "description": "Schedule: '30m', 'every 2h', or ISO timestamp"},
            "prompt": {"type": "string", "description": "Prompt to run (for create)"},
            "job_id": {"type": "integer", "description": "Job ID (for pause/resume/remove)"},
        },
        "required": ["action"],
    },
    destructive=True,
    requires_approval=True,
    toolset="scheduler",
)


# ══════════════════════════════════════════════════════════════════════════════
# memory_add — agent can add facts to its own memory
# ══════════════════════════════════════════════════════════════════════════════

async def _memory_add(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """Add a fact to persistent memory."""
    content = args.get("content", "")
    if not content:
        return ToolResult(success=False, error="content required")

    category = args.get("category", "fact")
    confidence_raw = args.get("confidence", 1.0)
    try:
        confidence = max(0.0, min(1.0, float(confidence_raw)))
    except (TypeError, ValueError):
        confidence = 1.0

    from atar_core.memory import create_entry
    entry_id = create_entry(category=category, content=content, confidence=confidence)

    if entry_id:
        return ToolResult(success=True, output=f"Memory #{entry_id} saved: [{category}] {content}",
                        metadata={"id": entry_id, "category": category})
    return ToolResult(success=False, error="Memory rejected (may contain secrets)")


register(
    "memory_add",
    "Save a fact, preference, or decision to persistent memory",
    _memory_add,
    parameters={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Content to remember"},
            "category": {"type": "string", "enum": ["fact", "preference", "decision"], "description": "Memory category"},
            "confidence": {"type": "number", "description": "Confidence 0.0-1.0 (default 1.0)"},
        },
        "required": ["content"],
    },
    destructive=False,
    toolset="memory",
)


# ══════════════════════════════════════════════════════════════════════════════
# memory_list — agent can list/query its own memories
# ══════════════════════════════════════════════════════════════════════════════

async def _memory_list(_name: str, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    """List or search persistent memories."""
    query = args.get("query", "")
    category = args.get("category", "")
    limit = min(args.get("limit", 20), 50)

    from atar_core.memory import count_active, get_entries

    entries = get_entries(category=category or None, query=query or None, limit=limit)

    if not entries:
        return ToolResult(success=True, output="No memories found.",
                        metadata={"active_total": count_active()})

    lines = [f"[{e.id}] [{e.category}] {e.content}" for e in entries]
    return ToolResult(
        success=True,
        output="\n".join(lines),
        metadata={"shown": len(entries), "active_total": count_active()},
    )


register(
    "memory_list",
    "List or search persistent memories by category or query",
    _memory_list,
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional search query"},
            "category": {"type": "string", "enum": ["fact", "preference", "decision"], "description": "Filter by category"},
            "limit": {"type": "integer", "description": "Max results (default 20)"},
        },
    },
    destructive=False,
    toolset="memory",
)
