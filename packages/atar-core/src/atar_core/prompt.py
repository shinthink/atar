"""ATAR prompt assembly — layered, stable prefix for prompt caching."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass


@dataclass
class PromptLayer:
    """A layer in the assembled system prompt."""
    name: str                     # "identity", "safety", "tools", etc.
    content: str                  # the prompt text
    stability: str = "session"    # "session" (never changes) or "turn" (changes per turn)


# ── SESSION-STABLE LAYERS ──

IDENTITY: PromptLayer = PromptLayer(
    name="identity",
    content="You are ATAR, an autonomous terminal AI agent. Built with clarity. Named for tranquility.",
    stability="session",
)

ACTION: PromptLayer = PromptLayer(
    name="action",
    content=(
        "CRITICAL RULES:\n"
        "- When asked to CREATE, WRITE, BUILD, or MAKE something — use write_file IMMEDIATELY.\n"
        "- Do NOT describe what you will do. Do NOT plan out loud. Just DO it.\n"
        "- Always produce a working deliverable backed by real tool output — not a description.\n"
        "- If a user asks you to create a file, write code, or build something, the deliverable "
        "is the actual file on disk, not a description of what the file would contain."
    ),
    stability="session",
)

SAFETY: PromptLayer = PromptLayer(
    name="safety",
    content=(
        "Never assume or fabricate the user's name.\n"
        "Never prefix responses with 'I will' or 'Saya akan'.\n"
        "Do not invent facts, URLs, or citations. Use tools to verify.\n"
        "When uncertain, ask — do not guess.\n"
    ),
    stability="session",
)

PLATFORM: PromptLayer = PromptLayer(
    name="platform",
    content=f"Platform: {platform.system()}. Shell: {os.environ.get('SHELL', 'bash')}.",
    stability="session",
)

TOOLS: PromptLayer = PromptLayer(
    name="tools",
    content=(
        "You have tools: web_search (DuckDuckGo), web_fetch (extract URL content), "
        "read_file, write_file, terminal, session_search, session_resume.\n"
        "Use them immediately — do not describe what you will do.\n"
        "For research: search → fetch top results → synthesize with citations.\n"
        "For coding: inspect → checkpoint → edit → test → verify.\n"
        "For simple chat: respond directly without tools.\n"
    ),
    stability="session",
)

INSTRUCTIONS: PromptLayer = PromptLayer(
    name="instructions",
    content=(
        "- Be concise. One-sentence answers preferred unless complexity demands more.\n"
        "- Match the user's language (Indonesian, English, etc).\n"
        "- Use Linux commands (ls, grep, find, etc). Never suggest open/start.\n"
        "- After tool results, synthesize into a final answer — don't keep searching.\n"
        "- Show evidence: file paths, URLs, exit codes, test results.\n"
    ),
    stability="session",
)


# ── TURN-STABLE LAYERS (may change per run) ──

def ephemeral_layer(session_id: str = "", model: str = "", cwd: str = "") -> PromptLayer:
    return PromptLayer(
        name="ephemeral",
        content=(
            f"Session: {session_id[:12] if session_id else 'new'}.\n"
            f"Model: {model}.\n"
            f"Working directory: {cwd}.\n"
        ),
        stability="turn",
    )


# ── ASSEMBLER ──

@dataclass
class AssembledPrompt:
    """Result of prompt assembly."""
    session_prefix: str    # stable across turns
    turn_prefix: str       # may change per turn (ephemeral)
    full: str              # combined

    def __str__(self) -> str:
        return self.full


def assemble(session_id: str = "", model: str = "", cwd: str = "", memory_profile: str = "default") -> AssembledPrompt:
    """Build a multi-layer system prompt with memory snapshot."""
    session_layers = [IDENTITY, ACTION, SAFETY, PLATFORM, TOOLS, INSTRUCTIONS]



    # Inject ATAR.md project context if present
    atar_md_path = os.path.join(os.getcwd(), "ATAR.md")
    if not os.path.exists(atar_md_path):
        atar_md_path = os.path.join(os.getcwd(), ".atar", "context.md")
    if os.path.exists(atar_md_path):
        try:
            with open(atar_md_path) as af:
                session_layers.append(PromptLayer(name="project_context", content=af.read()[:4000], stability="session"))
        except Exception:
            pass

    # Inject user model if present
    from atar_core.user_model import load_model, model_to_prompt
    um = model_to_prompt(load_model())
    if um:
        session_layers.append(PromptLayer(name="user_model", content=um, stability="session"))

    # Inject memory if present
    from atar_core.memory import get_entries
    entries = get_entries(limit=15)
    if entries:
        mem_text = "<memory>\n" + "\n".join(f"[{e.category}] {e.content}" for e in entries) + "\n</memory>"
        session_layers.append(PromptLayer(name="memory", content=mem_text, stability="session"))

    session_prefix = "\n\n".join(layer.content for layer in session_layers)

    ep = ephemeral_layer(session_id=session_id, model=model, cwd=cwd)

    return AssembledPrompt(
        session_prefix=session_prefix,
        turn_prefix=ep.content,
        full=f"{session_prefix}\n\n{ep.content}",
    )
