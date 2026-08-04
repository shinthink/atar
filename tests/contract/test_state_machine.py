"""Contract tests for AgentStateMachine."""

from __future__ import annotations

import pytest
from atar_core.state_machine import AgentState, AgentStateMachine, StateMachineError


@pytest.fixture
def sm() -> AgentStateMachine:
    return AgentStateMachine()


def test_initial_state_is_idle(sm: AgentStateMachine) -> None:
    assert sm.state == AgentState.IDLE


def test_valid_transition_idle_to_understanding(sm: AgentStateMachine) -> None:
    sm.transition(AgentState.UNDERSTANDING)
    assert sm.state == AgentState.UNDERSTANDING


def test_invalid_transition_raises(sm: AgentStateMachine) -> None:
    with pytest.raises(StateMachineError):
        sm.transition(AgentState.EXECUTING)  # cannot go IDLE → EXECUTING directly


def test_history_tracks_transitions(sm: AgentStateMachine) -> None:
    sm.transition(AgentState.UNDERSTANDING)
    sm.transition(AgentState.RETRIEVING_CONTEXT)
    assert len(sm.history) == 2
    assert sm.history[0] == (AgentState.IDLE, AgentState.UNDERSTANDING)


def test_can_transition(sm: AgentStateMachine) -> None:
    assert sm.can_transition(AgentState.UNDERSTANDING) is True
    assert sm.can_transition(AgentState.EXECUTING) is False


def test_completed_is_terminal(sm: AgentStateMachine) -> None:
    sm.transition(AgentState.UNDERSTANDING)
    sm.transition(AgentState.RETRIEVING_CONTEXT)
    sm.transition(AgentState.PLANNING)
    sm.transition(AgentState.RISK_REVIEW)
    sm.transition(AgentState.EXECUTING)
    sm.transition(AgentState.VERIFYING)
    sm.transition(AgentState.COMPLETED)
    assert sm.is_terminal() is True
    assert sm.can_transition(AgentState.IDLE) is False


def test_force_transition(sm: AgentStateMachine) -> None:
    sm.force(AgentState.FAILED)
    assert sm.state == AgentState.FAILED


def test_reset(sm: AgentStateMachine) -> None:
    sm.transition(AgentState.UNDERSTANDING)
    sm.reset()
    assert sm.state == AgentState.IDLE
    assert len(sm.history) == 0
