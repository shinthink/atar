"""ATAR agent orchestrator — with tool support."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from atar_models.requests import Message, ModelRequest
from atar_models.responses import ModelResponse
from atar_protocols import ModelProvider

from atar_core.event_bus import EventBus
from atar_core.state_machine import AgentState, AgentStateMachine, StateMachineError


@dataclass
class StreamCallbacks:
    on_delta: Callable[[str], Coroutine[Any, Any, None] | None] | None = None
    on_tool_call: Callable[[str, dict[str, Any]], Coroutine[Any, Any, None] | None] | None = None
    on_tool_result: Callable[[str, str], Coroutine[Any, Any, None] | None] | None = None
    on_done: Callable[[ModelResponse | None], Coroutine[Any, Any, None] | None] | None = None
    on_error: Callable[[str], Coroutine[Any, Any, None] | None] | None = None


@dataclass
class Agent:
    provider: ModelProvider
    system_prompt: str = "You are ATAR, an AI assistant that values clarity and precision."
    tools: list[Any] = field(default_factory=list)
    max_turns: int = 5
    session_id: str = ""
    event_bus: EventBus = field(default_factory=EventBus)
    state: AgentStateMachine = field(default_factory=AgentStateMachine)
    _messages: list[Message] = field(default_factory=list)

    async def run(
        self, user_input: str, callbacks: StreamCallbacks | None = None
    ) -> ModelResponse | None:
        cb = callbacks or StreamCallbacks()
        self.state.transition(AgentState.UNDERSTANDING, session_id=self.session_id)
        self._messages.append(Message(role="user", content=user_input))

        turn = 0
        while turn < self.max_turns:
            turn += 1
            request = ModelRequest(
                provider_id="atar",
                model="",
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

                # Execute tool calls if any — skip partial, dedup by id
                if tool_calls:
                    seen = set()
                    for tc in tool_calls:
                        tid = tc.get("id", "")
                        name = tc.get("name", "")
                        inp = tc.get("input") or {}
                        if not name or not inp:
                            continue  # skip partial tool calls
                        if tid and tid in seen:
                            continue
                        if tid:
                            seen.add(tid)
                        if cb.on_tool_call:
                            await cb.on_tool_call(name, inp)
                        result = await self._execute_tool(name, inp)
                        if cb.on_tool_result:
                            await cb.on_tool_result(name, result.output)
                        self._messages.append(Message(
                            role="user", content=f"Tool {name} result: {result.output}"
                        ))
                    continue  # next turn with tool results

                # No tool calls — but if final_text is empty after tool results, prompt model to synthesize
                if not final_text.strip() and len(self._messages) > 2:
                    self._messages.append(Message(
                        role="user",
                        content=(
                            "You have tool results above. "
                            "If web_search returned results, use web_fetch on the top 2 URLs to extract content. "
                            "Then synthesize a concise answer with sources. Do NOT say you will search — just act."
                        )
                    ))
                    continue  # retry with follow-up prompt

                # No tool calls — response is final
                self._messages.append(Message(role="assistant", content=final_text))
                response = ModelResponse(text=final_text, model="")
                if cb.on_done:
                    await cb.on_done(response) if callable(cb.on_done) else None
                self.state.transition(AgentState.COMPLETED)
                return response

            except StateMachineError:
                self.state.force(AgentState.FAILED)
                return None
            except Exception as exc:
                self.state.force(AgentState.FAILED)
                if cb.on_error:
                    await cb.on_error(str(exc)) if callable(cb.on_error) else None
                return None

        return ModelResponse(text="Max turns reached.")

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        from atar_models.tools import ToolContext
        from atar_tools.registry import execute as tool_execute
        ctx = ToolContext(metadata={"approved": True})
        return await tool_execute(name, args, ctx)

    def _tool_schemas(self) -> list[Any]:
        from atar_tools.registry import list_all
        return list_all()  # return Tool objects, not dicts

    def continue_conversation(self, user_input: str, callbacks: StreamCallbacks | None = None):
        return self.run(user_input, callbacks)

    def _format_messages(self) -> list[Message]:
        msgs = list(self._messages)
        if msgs and msgs[0].role != "system" and self.system_prompt:
            msgs.insert(0, Message(role="system", content=self.system_prompt))
        return msgs

    def history(self) -> list[Message]:
        return list(self._messages)
