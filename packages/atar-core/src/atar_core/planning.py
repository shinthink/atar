"""ATAR planning engine."""

from __future__ import annotations

from atar_models.planning import Plan

from atar_core.agent import Agent, StreamCallbacks

PLAN_PROMPT = """\
You are ATAR's planning engine. Produce a structured plan.

Format EXACTLY:
# Plan Title
Goal: <one sentence>
Tasks:
- Task description [LOW]
- Task description [MEDIUM]
- Task description [HIGH]

Risk: [LOW], [MEDIUM], [HIGH]. Use [HIGH] for destructive/network/external ops.
Only output the plan. No preamble."""


class PlanningEngine:
    def __init__(self, agent: Agent) -> None:
        self.agent = agent

    async def plan(self, goal: str) -> Plan:
        agent = Agent(provider=self.agent.provider, system_prompt=PLAN_PROMPT, max_turns=1)
        response = await agent.run(goal, StreamCallbacks())
        if not response:
            return Plan(goal=goal)
        return Plan.parse(response.text, goal=goal)

    async def classify_risks(self, plan: Plan) -> Plan:
        raw = plan.model_dump_json(indent=2)
        prompt = f"Classify risk:\n{raw}\nReply with JSON: task_id -> risk."
        response = await self.agent.run(prompt, StreamCallbacks())
        if response and response.text:
            import json
            try:
                risks = json.loads(response.text)
                for task in plan.tasks:
                    if task.id in risks:
                        task.risk = risks[task.id]
            except (json.JSONDecodeError, KeyError):
                pass
        return plan
