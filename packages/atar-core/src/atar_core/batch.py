"""ATAR batch + evaluation — Section 64 Step 17.

Batch: JSON input → parallel execution → results.
Eval: trajectory logging with scoring.
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any


class BatchRunner:
    """Run multiple prompts from JSON and collect results."""

    def __init__(self, provider_factory) -> None:
        self._pf = provider_factory

    async def run_batch(
        self, prompts: list[str], system: str = ""
    ) -> list[dict[str, Any]]:
        from atar_core.agent import Agent, StreamCallbacks

        async def _one(prompt: str) -> dict[str, Any]:
            provider = self._pf()
            agent = Agent(provider=provider, system_prompt=system or "Be concise.", max_turns=2)
            response = await agent.run(prompt, StreamCallbacks())
            return {
                "prompt": prompt,
                "response": response.text if response else "",
                "error": None if response else "no response",
            }

        return await asyncio.gather(*[_one(p) for p in prompts])

    @staticmethod
    def from_file(path: str) -> list[str]:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, dict) and "prompts" in data:
            return [str(p) for p in data["prompts"]]
        return []


class Evaluator:
    """Log evaluations with scoring for benchmark tracking."""

    def __init__(self, path: str = ".atar/evaluations.jsonl") -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(
        self,
        prompt: str,
        response: str,
        expected: str = "",
        score: float | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "prompt": prompt,
            "response": response[:1000],
            "expected": expected,
            "score": score,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def stats(self) -> dict[str, Any]:
        if not os.path.exists(self.path):
            return {"total": 0}
        scores = []
        with open(self.path) as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("score") is not None:
                    scores.append(entry["score"])
        return {
            "total": len(scores) + sum(1 for _ in open(self.path)) - len(scores),
            "scored": len(scores),
            "avg_score": sum(scores) / len(scores) if scores else None,
        }
