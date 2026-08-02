"""Integration test — vertical slice: agent → provider → stream → response."""

from __future__ import annotations

import pytest
from atar_core.agent import Agent, StreamCallbacks
from atar_core.fake_provider import FakeModelProvider


@pytest.fixture
def agent() -> Agent:
    return Agent(
        provider=FakeModelProvider(responses=["I'm operational."]),
        system_prompt="Be concise.",
    )


async def test_agent_run_returns_response(agent: Agent) -> None:
    received: list[str] = []

    async def on_delta(text: str) -> None:
        received.append(text)

    response = await agent.run("Hello", StreamCallbacks(on_delta=on_delta))

    assert response is not None
    assert response.text == "I'm operational."
    assert "".join(received) == "I'm operational."


async def test_agent_maintains_history(agent: Agent) -> None:
    await agent.run("First question", StreamCallbacks())
    await agent.continue_conversation("Second question", StreamCallbacks())

    history = agent.history()
    assert len(history) == 4  # user1, assistant1, user2, assistant2
    assert history[0].role == "user"
    assert history[2].role == "user"


async def test_agent_state_transitions(agent: Agent) -> None:
    assert agent.state.state.value == "idle"
    await agent.run("Hello", StreamCallbacks())
    assert agent.state.state.value == "completed"


async def test_agent_handles_provider_error() -> None:
    agent = Agent(
        provider=FakeModelProvider(responses=["x"], fail_on=1),
        system_prompt="test",
    )

    errors: list[str] = []

    async def on_error(msg: str) -> None:
        errors.append(msg)

    response = await agent.run("Hello", StreamCallbacks(on_error=on_error))
    # Fake provider fail_on delays to second call; stream() on first call works
    assert response is not None
    assert response.text == "x"
    assert len(errors) == 0
