"""ATAR agent orchestrator — with tool support and budget tracking."""

from __future__ import annotations

import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from atar_models.requests import Message, ModelRequest
from atar_models.responses import ModelResponse
from atar_protocols import ModelProvider

from atar_core.budgets import RunBudget, RunResult, TerminalState
from atar_core.event_bus import EventBus
from atar_core.state_machine import AgentState, AgentStateMachine, StateMachineError


@dataclass
class StreamCallbacks:
    on_delta: Callable[[str], Coroutine[Any, Any, None] | None] | None = None
    on_tool_call: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None] | None] | None = None
    on_tool_result: Callable[[str, str], Coroutine[Any, Any, None] | None] | None = None
    on_approval: Callable[[str, dict[str, Any]], Coroutine[Any, Any, bool] | None] | None = None
    get_rejection_feedback: Callable[[], str | None] | None = None
    on_done: Callable[[ModelResponse], Coroutine[Any, Any, None] | None] | None = None
    on_error: Callable[[str], Coroutine[Any, Any, None] | None] | None = None


@dataclass
class Agent:
    provider: ModelProvider
    max_turns: int = 8
    tools: list[Any] | None = None
    system_prompt: str = (
        "You are ATAR, an AI assistant that values clarity and precision. "
        "CRITICAL: Never describe an action you are about to take without immediately calling "
        "the corresponding tool in the same response. If you say you will do something, do it "
        "now — don't just announce it. When asked to create, write, build, or make something, "
        "use write_file now, not words about what you will create."
    )
    session_id: str = ""
    interactive: bool = True
    event_bus: EventBus | None = None
    state: AgentStateMachine = field(default_factory=AgentStateMachine)
    _messages: list[Message] = field(default_factory=list)
    _turn_count: int = 0

    async def run(self, user_input: str, callbacks: StreamCallbacks | None = None, budget: RunBudget | None = None, cancel_token: Any = None) -> RunResult:
        """Execute one full agent turn loop with structured result."""
        if budget is None:
            budget = RunBudget()
        cb = callbacks or StreamCallbacks()
        # Reset agent state if needed (allow re-entry from any terminal state)
        if self.state._state in {AgentState.COMPLETED, AgentState.FAILED, AgentState.IDLE}:
            self.state.force(AgentState.IDLE)
        self.state.transition(AgentState.UNDERSTANDING, session_id=self.session_id)
        self._messages.append(Message(role="user", content=user_input))

        turn = 0
        _narration_retry = 0  # max 2 retries for "let me do it" without tool call
        import time as _time
        budget.started_at = _time.monotonic()

        while budget.turns_remaining() > 0:
            if cancel_token and getattr(cancel_token, "cancelled", lambda: False)():
                return RunResult(state=TerminalState.CANCELLED, error="Cancelled by user", budget=budget.snapshot())
            if budget.is_exhausted():
                return RunResult(state=TerminalState.BUDGET_EXHAUSTED, budget=budget.snapshot())

            turn += 1
            self._turn_count = turn
            budget.record_turn()

            request = ModelRequest(
                provider_id="atar", model="",
                messages=self._format_messages(),
                cache_system=True,
                cache_tools=True,
            )
            if self.tools:
                request.tools = self._tool_schemas()

            try:
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []

                async for event in self.provider.stream(request):
                    if event.event_type == "text_delta" and event.text:
                        text_parts.append(event.text)
                        if cb.on_delta:
                            await cb.on_delta(event.text) if callable(cb.on_delta) else None
                    elif event.event_type == "tool_call":
                        tc = event.provider_metadata or {}
                        tool_calls.append(tc)

                final_text = "".join(text_parts)

                _had_tools_this_turn = bool(tool_calls)

                # Compute narration detection once
                _narration_patterns = [
                    r"let me", r"i'll", r"i will", r"now let me",
                    r"writing the", r"building the", r"creating the",
                    r"i now have", r"working on", r"mari saya",
                    r"saya akan", r"akan saya", r"time to write",
                ]
                _narration_re = re.compile("|".join(_narration_patterns), re.IGNORECASE)
                is_narrating = bool(_narration_re.search(final_text))
                if tool_calls:
                    normalized_calls = []
                    seen = set()
                    for tc in tool_calls:
                        tid = tc.get("id", "")
                        name = tc.get("name", "")
                        inp = tc.get("input") or {}
                        if not name:
                            continue
                        if tid and tid in seen:
                            continue
                        if tid:
                            seen.add(tid)
                        # Check repeated call budget
                        if budget.too_many_repeated(name):
                            self._messages.append(Message(
                                role="tool", tool_call_id=tid,
                                content=f"Tool {name} skipped: too many repeated calls."
                            ))
                            continue
                        if budget.tools_remaining() <= 0:
                            self._messages.append(Message(
                                role="tool", tool_call_id=tid,
                                content=f"Tool {name} skipped: tool call budget exhausted."
                            ))
                            continue
                        normalized_calls.append({"id": tid, "name": name, "arguments": inp})

                    self._messages.append(Message(
                        role="assistant",
                        content=final_text or None,
                        tool_calls=[{"id": c["id"], "name": c["name"], "input": c["arguments"]} for c in normalized_calls],
                    ))

                    for nc in normalized_calls:
                        budget.record_tool(nc["name"])
                        if cb.on_tool_call:
                            await cb.on_tool_call(nc["name"], nc["arguments"])
                        # Check approval before executing
                        if cb.on_approval:
                            approved = await cb.on_approval(nc["name"], nc["arguments"])
                            if not approved:
                                rejection_msg = f"Tool {nc['name']} rejected by user."
                                if hasattr(cb, "get_rejection_feedback"):
                                    fb = cb.get_rejection_feedback()
                                    if fb:
                                        rejection_msg += f" User feedback: {fb}"
                                self._messages.append(Message(
                                    role="tool", tool_call_id=nc["id"],
                                    content=rejection_msg,
                                ))
                                continue
                        result = await self._execute_tool(nc["name"], nc["arguments"])
                        if cb.on_tool_result:
                            await cb.on_tool_result(nc["name"], result.output)
                        # Truncate output for context efficiency, save full copy
                        from atar_core.output_truncation import save_full_output, truncate_tool_output
                        save_full_output(self._turn_count, result.output or "")
                        truncated = truncate_tool_output(result.output or "", tool_name=nc["name"])
                        self._messages.append(Message(
                            role="tool",
                            tool_call_id=nc["id"],
                            content=f"Tool {nc['name']} result: {truncated}\nError: {result.error}" if result.error else f"Tool {nc['name']} result: {truncated}",
                        ))
                    # If model was narrating intent in this turn, add nudge before next turn
                    if is_narrating:
                        self._messages.append(Message(role="user", content=(
                            "You have the research results. Now execute: call write_file or the "
                            "appropriate tool immediately. Do not describe — act."
                        )))
                    continue

                # Check if model is narrating intent ("Let me create...") without acting
                # Reuse _narration_patterns from above
                _narration_re = re.compile("|".join(_narration_patterns), re.IGNORECASE)
                is_narrating = bool(_narration_re.search(final_text))
                if is_narrating and not _had_tools_this_turn and budget.turns_remaining() > 0:
                    if _narration_retry >= 2:
                        return RunResult(
                            state=TerminalState.FAILED,
                            error="Model kept describing actions without calling tools after 2 retries.",
                            budget=budget.snapshot(),
                        )
                    _narration_retry += 1
                    self._messages.append(Message(role="assistant", content=final_text))
                    self._messages.append(Message(role="user", content=(
                        "You said you would do this — now actually call the tool instead of "
                        "describing it. Do not narrate further, just call the tool."
                    )))
                    continue

                # Check if empty response — inject follow-up
                if not final_text.strip():
                    tool_msgs = [m for m in self._messages if getattr(m, "role", "") == "tool"]
                    if tool_msgs and budget.turns_remaining() > 0:
                        self._messages.append(Message(role="user", content=(
                            "You received tool results above. "
                            "Synthesize a direct concise answer. "
                            "Do NOT say you will search — just use web_fetch then answer."
                        )))
                        continue
                    return RunResult(state=TerminalState.COMPLETED, final_text="", budget=budget.snapshot())

                # Final response
                self._messages.append(Message(role="assistant", content=final_text))
                self.state.transition(AgentState.COMPLETED)

                # Update user model from conversation (local computation, no LLM)
                from atar_core.user_model import load_model, update_from_messages
                raw_msgs = [{"role": getattr(m, "role", ""), "content": str(getattr(m, "content", ""))} for m in self._messages]
                update_from_messages(load_model(), raw_msgs)

                # Background tasks — throttled, cheap provider, togglable
                import asyncio

                from atar_core.background import get_background_provider_config, get_throttle, is_memory_enabled, is_skills_auto_enabled
                throttle = get_throttle()
                if self._turn_count % throttle == 0:
                    bp, bm = get_background_provider_config()
                    if bp and is_memory_enabled():
                        asyncio.create_task(_extract_memory(self, budget, bp, bm))
                    if bp and is_skills_auto_enabled():
                        asyncio.create_task(_maybe_create_skill(self, budget, bp, bm))

                # Memory nudge: check if user should review memories
                nudge_triggered = False
                try:
                    from atar_core.memory_nudge import should_nudge
                    if should_nudge():
                        nudge_triggered = True
                except Exception:
                    pass

                return RunResult(
                    state=TerminalState.COMPLETED,
                    final_text=final_text,
                    budget=budget.snapshot(),
                    evidence=[{"nudge_memory": True}] if nudge_triggered else [],
                )

            except StateMachineError:
                self.state.force(AgentState.FAILED)
                return RunResult(state=TerminalState.FAILED, error="State machine error", budget=budget.snapshot())
            except Exception as exc:
                self.state.force(AgentState.FAILED)
                if cb.on_error:
                    await cb.on_error(str(exc)) if callable(cb.on_error) else None
                return RunResult(state=TerminalState.FAILED, error=str(exc), budget=budget.snapshot())

        return RunResult(state=TerminalState.BUDGET_EXHAUSTED, budget=budget.snapshot())

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        from atar_models.tools import ToolContext
        from atar_tools.registry import execute as tool_execute
        # Interactive mode: auto-approve tool calls (user can Ctrl+C)
        approved = getattr(self, "interactive", True)
        ctx = ToolContext(metadata={
            "session_id": self.session_id,
            "approved": approved,
        })
        return await tool_execute(name, args, ctx)
    def _tool_schemas(self) -> list[Any]:
        from atar_tools.registry import list_all
        from atar_tools.toolsets import get_active_toolset_names
        active = get_active_toolset_names()
        all_tools = list_all()
        if active:
            return [t for t in all_tools if getattr(t, "toolset", "") in active]
        return all_tools

    def continue_conversation(self, user_input: str, callbacks: StreamCallbacks | None = None):
        return self.run(user_input, callbacks)

    def undo_last_turn(self, n: int = 1) -> list[str]:
        """Restore the last n checkpointed files (disk-based). History stays intact."""
        from atar_tools.tools.checkpoints import list_checkpoints, restore_checkpoint
        cps = list_checkpoints()[:n]
        restored = []
        for cp in cps:
            if restore_checkpoint(cp.get("id", "")):
                restored.append(cp.get("original", cp.get("file_path", "")))
        return restored

    def list_checkpoints(self) -> list[dict]:
        """Expose recent checkpoints (disk-based)."""
        from atar_tools.tools.checkpoints import list_checkpoints
        return list_checkpoints()

    def retry_last_turn(self) -> str | None:
        """Return the last user message for retry (without modifying history)."""
        for i in range(len(self._messages) - 1, -1, -1):
            if self._messages[i].role == "user":
                return self._messages[i].content
        return None

    def _format_messages(self) -> list[Message]:
        msgs = list(self._messages)
        if self.system_prompt:
            if msgs and msgs[0].role == "system":
                msgs[0] = Message(role="system", content=self.system_prompt)
            else:
                msgs.insert(0, Message(role="system", content=self.system_prompt))
        return msgs

    def history(self) -> list[Message]:
        return list(self._messages)


async def _extract_memory(agent, budget, bg_provider_id: str = "", bg_model: str = "") -> None:
    """Async, non-blocking: extract memory entries from last N turns via cheap LLM."""
    if not bg_provider_id:
        return
    try:
        from atar_core.background import record_bg_tokens
        from atar_core.memory import create_entry
        msgs = agent._messages[-6:]
        if len(msgs) < 4:
            return
        transcript = "\n".join(
            f"[{getattr(m, 'role', '?')}] {str(getattr(m, 'content', ''))[:300]}"
            for m in msgs
        )
        prompt = (
            "You are a memory curator. Review this conversation excerpt and output "
            "up to 5 structured memory entries as JSON array. Each entry: "
            '{"category":"fact|preference|decision","content":"<single sentence>","confidence":0.0-1.0}. '
            "Only include entries with confidence >= 0.6. Return ONLY valid JSON array, no other text.\n\n"
            f"{transcript}"
        )
        from atar_models.requests import Message, ModelRequest

        from atar_core.provider_registry import get_provider
        bg_provider = get_provider(bg_provider_id)
        if not bg_provider:
            return
        req = ModelRequest(provider_id=bg_provider_id, model=bg_model, messages=[
            Message(role="user", content=prompt),
        ])
        text = ""
        tokens_used = 0
        async for event in bg_provider.stream(req):
            if hasattr(event, "text") and event.text:
                text += event.text
            if hasattr(event, "provider_metadata"):
                meta = event.provider_metadata or {}
                tokens_used += meta.get("usage", {}).get("total_tokens", 0)
        record_bg_tokens("memory", tokens_used)
        import json
        try:
            entries = json.loads(text.strip())
        except json.JSONDecodeError:
            return
        for entry in entries:
            if isinstance(entry, dict) and entry.get("confidence", 0) >= 0.6:
                create_entry(
                    category=entry.get("category", "fact"),
                    content=entry["content"],
                    source_session_id=getattr(agent, "session_id", ""),
                    confidence=entry["confidence"],
                )
    except Exception:
        pass  # fire-and-forget — never block the user


async def _maybe_create_skill(agent, budget, bg_provider_id: str = "", bg_model: str = "") -> None:
    """After session: if >=4 tool calls, ask cheap model for skill draft → pending."""
    if not bg_provider_id:
        return
    try:
        from atar_core.background import record_bg_tokens
        tools_called = sum(1 for m in agent._messages if getattr(m, 'role', '') == 'tool')
        if tools_called < 4:
            return
        transcript = "\n".join(
            f"[{getattr(m, 'role', '?')}] {str(getattr(m, 'content', ''))[:200]}"
            for m in agent._messages[-12:]
        )
        prompt = (
            "You are evaluating whether a reusable skill should be created from this session. "
            "If the session involved solving a non-trivial, repeatable task with tool calls, "
            "output a SKILL.md draft. Otherwise output SKIP.\n\n"
            "Format if creating:\n"
            "---\n"
            "name: skill-name\n"
            "description: One-line description\n"
            "trigger_hints: [phrase1, phrase2]\n"
            "---\n"
            "# Skill Name\n\nStep-by-step procedure...\n\n"
            f"Session transcript:\n{transcript}"
        )
        from atar_models.requests import Message, ModelRequest

        from atar_core.provider_registry import get_provider
        bg_provider = get_provider(bg_provider_id)
        if not bg_provider:
            return
        req = ModelRequest(provider_id=bg_provider_id, model=bg_model, messages=[
            Message(role="user", content=prompt),
        ])
        text = ""
        tokens_used = 0
        async for event in bg_provider.stream(req):
            if hasattr(event, "text") and event.text:
                text += event.text
            if hasattr(event, "provider_metadata"):
                meta = event.provider_metadata or {}
                tokens_used += meta.get("usage", {}).get("total_tokens", 0)
        record_bg_tokens("skill", tokens_used)
        if "SKIP" in text[:20]:
            return
        from atar_core.skills import get_skill_manager
        mgr = get_skill_manager()
        mgr.save_pending(text)
    except Exception:
        pass  # fire-and-forget
