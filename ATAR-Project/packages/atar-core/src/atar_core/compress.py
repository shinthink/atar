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
        role = getattr(m, "role", "?")
        content = str(getattr(m, "content", ""))[:200]
        lines.append(f"[{role}] {content}")
    full = "\n".join(lines)
    compress_prompt = (
        f"Summarize this conversation into a dense context paragraph preserving "
        f"all facts, decisions, and important state:\n\n{full}\n\nSUMMARY:"
    )
    try:
        sub_result = await agent.run(compress_prompt)
        summary = sub_result.final_text or "Compressed."
    except Exception:
        summary = f"[Compressed {len(to_compress)} messages]"
    # Replace compressed section with summary
    from atar_models.requests import Message
    new_msgs = [m for m in agent._messages if m.role == "system"]
    new_msgs.append(Message(role="system", content=f"[Compressed context]\n{summary}"))
    new_msgs.extend([m for m in tail if m.role != "system"])
    agent._messages = new_msgs
    return f"Compressed {len(to_compress)} messages → {len(summary)} chars context."
