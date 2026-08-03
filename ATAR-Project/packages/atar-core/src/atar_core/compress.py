"""ATAR context compression — summarize history to free tokens."""

from __future__ import annotations


async def compress_history(agent, keep_last: int = 4) -> str:
    """Summarize conversation, keep N last msgs. Returns summary text."""
    msgs = agent._messages
    if len(msgs) <= keep_last + 2:
        return "History too short to compress."
    to_compress = msgs[:-keep_last]
    tail = msgs[-keep_last:]

    # Build compression prompt
    lines = []
    for m in to_compress:
        if getattr(m, "role", "") == "system":
            continue
        role = getattr(m, "role", "?")
        content = str(getattr(m, "content", ""))[:200]
        lines.append(f"[{role}] {content}")

    full = "\n".join(lines)
    compress_prompt = (
        f"Summarize this conversation into a dense context paragraph preserving "
        f"all facts, decisions, and important state:\n\n{full}"
    )

    summary = f"[Compressed {len(to_compress)} messages]"
    try:
        # Use a separate budget-limited call, not the full agent loop
        from atar_models.requests import Message, ModelRequest
        from atar_core.budgets import RunBudget
        sub_budget = RunBudget(max_turns=1, max_tool_calls=0, max_time_seconds=30)

        # Build minimal request for compression
        req = ModelRequest(
            provider_id="atar", model="",
            messages=[
                Message(role="system", content="You are a summarizer. Return ONLY the summary, no extra text."),
                Message(role="user", content=compress_prompt),
            ],
        )
        # Stream response directly from provider
        text_parts = []
        async for event in agent.provider.stream(req):
            if event.event_type == "text_delta" and event.text:
                text_parts.append(event.text)
        compressed = "".join(text_parts).strip()
        if compressed:
            summary = compressed
    except Exception:
        pass  # fall back to placeholder summary

    # Replace compressed section with summary
    from atar_models.requests import Message
    new_msgs = [m for m in agent._messages if m.role == "system"]
    new_msgs.append(Message(role="system", content=f"[Compressed context]\n{summary}"))
    new_msgs.extend([m for m in tail if m.role != "system"])
    agent._messages = new_msgs
    return f"Compressed {len(to_compress)} messages → {len(summary)} chars context."
