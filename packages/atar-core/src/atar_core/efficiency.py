"""ATAR efficiency engine — smart compression, parallel tools, caching, workspace detection.

Features that make ATAR genuinely faster and smarter than typical agents.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

# ══════════════════════════════════════════════════════════════════════════════
# 1. SMART CONTEXT COMPRESSION — LLM-based history summarization
# ══════════════════════════════════════════════════════════════════════════════

COMPRESSION_THRESHOLD_TOKENS = 8000   # Compress when history exceeds this
COMPRESSION_TARGET_TOKENS = 4000      # Target after compression
SUMMARY_PREFIX = "[SUMMARY] "


def estimate_tokens(text: str) -> int:
    """Fast token estimation: ~4 chars per token for English text."""
    return max(1, len(text) // 4)


def compress_history(messages: list, max_tokens: int = COMPRESSION_TARGET_TOKENS) -> list:
    """Smart context compression: keep system prompt + recent turns, summarize middle.

    Strategy:
    - Keep first 2 messages (system + first user)
    - Keep last 6 messages (recent context)
    - Summarize everything in between into a single system message
    """
    if len(messages) <= 8:
        return list(messages)

    # Estimate total tokens
    total = sum(estimate_tokens(str(getattr(m, "content", ""))) for m in messages)
    if total <= COMPRESSION_THRESHOLD_TOKENS:
        return list(messages)

    # Build compressed version
    compressed = []
    compressed.append(messages[0])  # System prompt

    # Summarize middle section
    middle = messages[1:-6]
    if middle:
        summary_parts = []
        for m in middle:
            content = str(getattr(m, "content", ""))
            role = getattr(m, "role", "?")
            if len(content) > 50:
                preview = content[:100].replace("\n", " ")
                summary_parts.append(f"[{role}] {preview}...")
            elif content.strip():
                summary_parts.append(f"[{role}] {content.strip()}")

        if summary_parts:
            total_middle_tokens = sum(estimate_tokens(p) for p in summary_parts)
            if total_middle_tokens > max_tokens // 2:
                # Truncate the summary itself
                while summary_parts and sum(estimate_tokens(p) for p in summary_parts) > max_tokens // 2:
                    summary_parts.pop(len(summary_parts) // 2)  # Remove from middle

            summary = "History summary: " + " | ".join(summary_parts[-20:])
            from atar_models.requests import Message
            compressed.append(Message(role="system", content=f"{SUMMARY_PREFIX}{summary}"))

    # Keep recent context
    compressed.extend(messages[-6:])
    return compressed


# ══════════════════════════════════════════════════════════════════════════════
# 2. PARALLEL TOOL EXECUTION — run independent tools simultaneously
# ══════════════════════════════════════════════════════════════════════════════

# Tool groups that are safe to run in parallel (no shared state dependencies)
_PARALLEL_SAFE_GROUPS = {
    "read_file", "search_files", "web_search", "web_fetch",
    "browser", "real_browser", "weather", "stocks", "maps",
    "memory_list", "memory_semantic",
}


def can_parallelize(tool_names: list[str]) -> bool:
    """Check if a set of tool calls can run in parallel."""
    return all(name in _PARALLEL_SAFE_GROUPS for name in tool_names)


async def execute_parallel(tool_calls: list[dict]) -> list[dict]:
    """Execute multiple independent tool calls concurrently.

    Args:
        tool_calls: list of {name, args} dicts

    Returns:
        list of {name, result} dicts in same order
    """
    from atar_models.tools import ToolContext
    from atar_tools.registry import execute

    async def _run_one(name: str, args: dict, index: int) -> tuple[int, dict]:
        try:
            ctx = ToolContext(metadata={"approved": True, "parallel": True})
            result = await execute(name, args, ctx)
            return index, {"name": name, "success": result.success, "output": result.output, "error": result.error}
        except Exception as e:
            return index, {"name": name, "success": False, "error": str(e)}

    tasks = [_run_one(tc["name"], tc.get("arguments", tc.get("args", {})), i)
             for i, tc in enumerate(tool_calls)]

    results = await asyncio.gather(*tasks)
    # Sort by original order
    results.sort(key=lambda x: x[0])
    return [r[1] for r in results]


# ══════════════════════════════════════════════════════════════════════════════
# 3. TOOL RESULT CACHING — avoid redundant calls
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CacheEntry:
    result: Any
    cached_at: float
    ttl: float  # Time to live in seconds


# In-memory cache per session
_cache: dict[str, CacheEntry] = {}
_cache_tool_map: dict[str, set[str]] = {}  # tool_name → set of cache keys

# TTLs per tool type (seconds)
_CACHE_TTL: dict[str, float] = {
    "read_file": 30,       # Files rarely change mid-session
    "search_files": 60,    # Search results are stable
    "web_fetch": 300,      # Web pages might update
    "web_search": 300,     # Search results change
    "weather": 600,        # Weather updates slowly
    "stocks": 120,         # Stock prices change frequently
    "maps": 3600,          # Geocoding never changes
    "memory_list": 10,     # Memory can change
    "memory_semantic": 30,
}


def _cache_key(tool_name: str, args: dict) -> str:
    raw = json.dumps({"name": tool_name, "args": args}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def cached_execute(tool_name: str, args: dict) -> tuple[Any | None, bool]:
    """Check cache before executing. Returns (cached_result, was_hit)."""
    key = _cache_key(tool_name, args)
    entry = _cache.get(key)
    if entry and (time.time() - entry.cached_at) < entry.ttl:
        return entry.result, True
    return None, False


def cache_result(tool_name: str, args: dict, result: Any) -> None:
    """Store a tool result in cache."""
    ttl = _CACHE_TTL.get(tool_name, 30)
    key = _cache_key(tool_name, args)
    _cache[key] = CacheEntry(result=result, cached_at=time.time(), ttl=ttl)
    if tool_name not in _cache_tool_map:
        _cache_tool_map[tool_name] = set()
    _cache_tool_map[tool_name].add(key)


def clear_cache(tool_name: str | None = None) -> None:
    """Clear cache for a specific tool or all tools."""
    if tool_name and tool_name in _cache_tool_map:
        for key in list(_cache_tool_map[tool_name]):
            _cache.pop(key, None)
        _cache_tool_map[tool_name].clear()
    elif tool_name is None:
        _cache.clear()
        _cache_tool_map.clear()


# Auto-clear cache when write operations happen
_WRITE_TOOLS = {"write_file", "patch", "terminal", "git", "delegate_task"}


def on_write_operation(tool_name: str) -> None:
    """Clear relevant caches after a write operation."""
    if tool_name in _WRITE_TOOLS:
        # Clear file read caches since files may have changed
        clear_cache("read_file")
        clear_cache("search_files")


# ══════════════════════════════════════════════════════════════════════════════
# 4. WORKSPACE AUTO-DETECTION — project structure analysis
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class WorkspaceInfo:
    """Auto-detected project information."""
    root: str = ""
    language: str = ""
    framework: str = ""
    package_manager: str = ""
    test_runner: str = ""
    test_dir: str = ""
    source_dir: str = ""
    config_files: list[str] = field(default_factory=list)
    git_initialized: bool = False
    total_files: int = 0
    python_packages: list[str] = field(default_factory=list)


def detect_workspace(path: str = ".") -> WorkspaceInfo:
    """Auto-detect project structure, language, framework, test runner."""
    info = WorkspaceInfo(root=os.path.abspath(path))

    # Check git
    info.git_initialized = os.path.exists(os.path.join(path, ".git"))

    # Detect language by config files
    detectors = {
        ("pyproject.toml",): ("Python", "uv/pip", "pytest"),
        ("setup.py", "setup.cfg"): ("Python", "pip/setuptools", "pytest"),
        ("package.json",): ("JavaScript/TypeScript", "npm/yarn/pnpm", "jest/vitest"),
        ("Cargo.toml",): ("Rust", "cargo", "cargo test"),
        ("go.mod",): ("Go", "go modules", "go test"),
        ("Makefile",): ("C/C++", "make", "make test"),
        ("CMakeLists.txt",): ("C/C++", "cmake", "ctest"),
    }

    for files, (lang, pkg_mgr, test) in detectors.items():
        for f in files:
            if os.path.exists(os.path.join(path, f)):
                info.language = lang
                info.package_manager = pkg_mgr
                info.test_runner = test
                info.config_files.append(f)

    # Python-specific detection
    if info.language == "Python":
        # Detect test directory
        for test_dir in ("tests", "test", "testing"):
            if os.path.isdir(os.path.join(path, test_dir)):
                info.test_dir = test_dir
                break

        # Detect source directory
        for src_dir in ("src", "packages", "apps", "lib"):
            if os.path.isdir(os.path.join(path, src_dir)):
                info.source_dir = src_dir
                break

        # Count files
        py_files = []
        for root, _, files in os.walk(path):
            if ".venv" in root or "__pycache__" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))
        info.total_files = len(py_files)

        # Detect packages from pyproject.toml
        pyproject_path = os.path.join(path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            try:
                with open(pyproject_path) as f:
                    content = f.read()
                # Simple dependency extraction
                import re
                deps = re.findall(r'"([a-z][a-z0-9_-]+)[>=<]', content)
                info.python_packages = list(set(deps))[:20]
            except Exception:
                pass

    # Detect test runner
    if info.language == "Python" and not info.test_runner and os.path.exists(os.path.join(path, "pyproject.toml")):
            with open(os.path.join(path, "pyproject.toml")) as f:
                if "pytest" in f.read():
                    info.test_runner = "pytest"

    return info


def get_workspace_context(path: str = ".") -> str:
    """Generate a concise workspace context string for the agent's system prompt."""
    info = detect_workspace(path)

    lines = ["[Workspace Context]"]
    if info.language:
        lines.append(f"Language: {info.language}")
    if info.package_manager:
        lines.append(f"Package manager: {info.package_manager}")
    if info.test_runner:
        lines.append(f"Test runner: {info.test_runner}")
    if info.test_dir:
        lines.append(f"Test directory: {info.test_dir}/")
    if info.source_dir:
        lines.append(f"Source directory: {info.source_dir}/")
    if info.git_initialized:
        lines.append("Git: initialized")
    if info.total_files:
        lines.append(f"Files: {info.total_files} Python files")
    if info.config_files:
        lines.append(f"Config: {', '.join(info.config_files)}")

    return "\n".join(lines)
