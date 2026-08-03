"""ATAR agent orchestrator — with tool support and budget tracking."""

from __future__ import annotations

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
    on_done: Callable[[ModelResponse], Coroutine[Any, Any, None] | None] | None = None
    on_error: Callable[[str], Coroutine[Any, Any, None] | None] | None = None


@dataclass
class Agent:
    provider: ModelProvider
    max_turns: int = 8
    tools: list[Any] | None = None
    system_prompt: str = "You are ATAR, an AI assistant that values clarity and precision."
    session_id: str = ""
    interactive: bool = True
    event_bus: EventBus | None = None
    state: AgentStateMachine = field(default_factory=AgentStateMachine)
    _messages: list[Message] = field(default_factory=list)

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
        import time as _time
        budget.started_at = _time.monotonic()

        while budget.turns_remaining() > 0:
            if cancel_token and getattr(cancel_token, "cancelled", lambda: False)():
                return RunResult(state=TerminalState.CANCELLED, error="Cancelled by user", budget=budget.snapshot())
            if budget.is_exhausted():
                return RunResult(state=TerminalState.BUDGET_EXHAUSTED, budget=budget.snapshot())

            turn += 1
            budget.record_turn()

            request = ModelRequest(
                provider_id="atar", model="",
                messages=self._format_messages(),
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

                if tool_calls:
                    normalized_calls = []
                    seen = set()
                    for tc in tool_calls:
                        tid = tc.get("id", "")
                        name = tc.get("name", "")
                        inp = tc.get("input") or {}
                        if not name or not inp:
                            continue
                        if tid and tid in seen:
                            continue
                        if tid:
                            seen.add(tid)
                        # Check repeated call budget
                        if budget.too_many_repeated(name):
                            return RunResult(state=TerminalState.BUDGET_EXHAUSTED, budget=budget.snapshot())
                        if budget.tools_remaining() <= 0:
                            return RunResult(state=TerminalState.BUDGET_EXHAUSTED, budget=budget.snapshot())
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
                                self._messages.append(Message(
                                    role="tool", tool_call_id=nc["id"],
                                    content=f"Tool {nc['name']} rejected by user.",
                                ))
                                continue
                        result = await self._execute_tool(nc["name"], nc["arguments"])
                        if cb.on_tool_result:
                            await cb.on_tool_result(nc["name"], result.output)
                        self._messages.append(Message(
                            role="tool",
                            tool_call_id=nc["id"],
                            content=f"Tool {nc['name']} result: {result.output}\nError: {result.error}" if result.error else f"Tool {nc['name']} result: {result.output}",
                        ))
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

                # Update user model from conversation
                from atar_core.user_model import load_model, update_from_messages
                raw_msgs = [{"role": getattr(m, "role", ""), "content": str(getattr(m, "content", ""))} for m in self._messages]
                update_from_messages(load_model(), raw_msgs)
                # Non-blocking memory extraction (fire-and-forget)
                import asyncio
                asyncio.create_task(_extract_memory(self, budget))
                asyncio.create_task(_maybe_create_skill(self, budget))
                return RunResult(state=TerminalState.COMPLETED, final_text=final_text, budget=budget.snapshot())

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
        return list_all()

    def continue_conversation(self, user_input: str, callbacks: StreamCallbacks | None = None):
        return self.run(user_input, callbacks)

    def undo_last_turn(self) -> str | None:
        """Undo last user+assistant turn. Returns the removed user message text or None."""
        msgs = self._messages
        if not msgs:
            return None
        # Find last user message
        last_user_idx = -1
        last_user_text = None
        for i in range(len(msgs) - 1, -1, -1):
            if msgs[i].role == "user":
                last_user_idx = i
                last_user_text = msgs[i].content or ""
                break
        if last_user_idx < 0:
            return None
        # Remove from last user to end (includes assistant, tool calls, tool results)
        msgs[last_user_idx:]
        self._messages = msgs[:last_user_idx]
        # Return the last non-system message as context
        return last_user_text[:50] if last_user_text else None

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


async def _extract_memory(agent, budget) -> None:
    """Async, non-blocking: extract memory entries from last N turns via LLM."""
    try:
        from atar_core.memory import create_entry
        msgs = agent._messages[-6:]  # last 3 turns (user+assistant)
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
        req = ModelRequest(provider_id="", model="", messages=[
            Message(role="user", content=prompt),
        ])
        text = ""
        async for event in agent.provider.stream(req):
            if hasattr(event, "text") and event.text:
                text += event.text
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


async def _maybe_create_skill(agent, budget) -> None:
    """After session: if >=4 tool calls, ask model for skill draft → pending."""
    try:
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
        req = ModelRequest(provider_id="", model="", messages=[
            Message(role="user", content=prompt),
        ])
        text = ""
        async for event in agent.provider.stream(req):
            if hasattr(event, "text") and event.text:
                text += event.text
        if text.strip() == "SKIP" or "SKIP" in text[:20]:
            return
        # Extract skill name from frontmatter
        import re
        name_match = re.search(r'name:\s*(\S+)', text)
        desc_match = re.search(r'description:\s*(.+)', text)
        skill_name = name_match.group(1) if name_match else f"skill-{tools_called}"
        skill_desc = desc_match.group(1).strip() if desc_match else ""
        from atar_core.skills import get_skill_manager
        mgr = get_skill_manager()
        ok = mgr.propose(skill_name, text, description=skill_desc)
        if ok:
            import logging
            logging.getLogger("atar.skills").info(f"Skill proposed: {skill_name}")
    except Exception:
        pass  # fire-and-forget
