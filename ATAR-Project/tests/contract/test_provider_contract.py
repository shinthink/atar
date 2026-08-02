"""Contract tests for ModelProvider protocol — per blueprint Section 6.14.

Every provider (real and fake) must pass these tests before integration.
"""

from __future__ import annotations

import pytest_asyncio
from atar_models.requests import Message, ModelRequest

from tests.fake_services.fake_provider import FakeModelProvider


@pytest_asyncio.fixture
async def fake() -> FakeModelProvider:
    return FakeModelProvider()


async def test_complete_returns_response(fake: FakeModelProvider) -> None:
    request = ModelRequest(
        provider_id="fake",
        model="fake-model-v1",
        messages=[Message(role="user", content="Hello")],
    )
    response = await fake.complete(request)
    assert response.text == "Fake response."
    assert response.model == "fake-model-v1"


async def test_complete_with_multiple_responses() -> None:
    provider = FakeModelProvider(responses=["First.", "Second."])
    r1 = await provider.complete(ModelRequest(provider_id="fake"))
    r2 = await provider.complete(ModelRequest(provider_id="fake"))
    assert r1.text == "First."
    assert r2.text == "Second."


async def test_complete_failure_on_nth_call() -> None:
    provider = FakeModelProvider(fail_on=2)
    await provider.complete(ModelRequest(provider_id="fake"))
    try:
        await provider.complete(ModelRequest(provider_id="fake"))
        raise AssertionError("Expected RuntimeError")
    except RuntimeError:
        pass


async def test_stream_yields_events(fake: FakeModelProvider) -> None:
    events = []
    async for event in fake.stream(ModelRequest(provider_id="fake")):
        events.append(event)
    assert len(events) > 0


async def test_capabilities(fake: FakeModelProvider) -> None:
    caps = await fake.capabilities()
    assert caps.text is True
    assert caps.streaming is False


async def test_count_tokens(fake: FakeModelProvider) -> None:
    from atar_models.requests import TokenCountRequest

    req = TokenCountRequest(model="fake", messages=[Message(role="user", content="hello world")])
    count = await fake.count_tokens(req)
    assert count == 2


async def test_health_check(fake: FakeModelProvider) -> None:
    health = await fake.health_check()
    assert health.status == "healthy"
