"""Unit tests for backend.agents.workflows — Workflow patterns.

Tests use fixture agents (dummy agents returning canned data), not live LLM calls.
"""

import pytest
import asyncio
from typing import Any

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus, ObservationTimeoutError
from backend.agents.types import AgentRole, AgentBudget, ResearchFindings, ReviewCritique
from backend.agents.workflows import SequentialWorkflow, ParallelWorkflow, DebateWorkflow


# ── Fixture agents ───────────────────────────────────────────────

class StubResearcher(BaseAgent):
    role = AgentRole.RESEARCHER
    async def run(self, context, bus):
        return ResearchFindings(
            market_data={"tam": "50B", "source": "stub"},
            project_data={"title": context.get("title", "TestCo")},
            sources=["https://stub.com"],
        )


class StubAnalyst(BaseAgent):
    role = AgentRole.ANALYST
    async def run(self, context, bus):
        return {"metrics": {"score": 0.85}, "confidence": 0.9}


class StubSynthesizer(BaseAgent):
    role = AgentRole.SYNTHESIZER

    def __init__(self, approve_on_round: int = 1, **kwargs):
        super().__init__(**kwargs)
        self._call_count = 0
        self._approve_on_round = approve_on_round

    async def run(self, context, bus):
        self._call_count += 1
        has_critique = "review_critique" in context
        return {
            "category": "B2B SaaS",
            "scores": {"innovation": 80},
            "revision_applied": has_critique,
            "round": self._call_count,
        }


class StubReviewer(BaseAgent):
    role = AgentRole.REVIEWER

    def __init__(self, approve_on_round: int = 1, **kwargs):
        super().__init__(**kwargs)
        self._call_count = 0
        self._approve_on_round = approve_on_round

    async def run(self, context, bus):
        self._call_count += 1
        approved = self._call_count >= self._approve_on_round
        return ReviewCritique(
            approved=approved,
            issues=[] if approved else ["Needs improvement"],
            severity="none" if approved else "minor",
            revision_notes=None if approved else "Please revise",
        )


class FailingAgent(BaseAgent):
    role = AgentRole.ANALYST
    async def run(self, context, bus):
        raise RuntimeError("Intentional failure")


class SlowAgent(BaseAgent):
    role = AgentRole.RESEARCHER
    async def run(self, context, bus):
        await asyncio.sleep(0.5)
        return {"slow": True}


# ── SequentialWorkflow ───────────────────────────────────────────

class TestSequentialWorkflow:
    @pytest.mark.asyncio
    async def test_runs_agents_in_order(self):
        workflow = SequentialWorkflow()
        agents = [StubResearcher(), StubAnalyst()]
        bus = AgentContextBus()
        result = await workflow.execute(agents, {"title": "TestCo"}, bus)

        assert "metrics" in result  # Analyst's output (last agent)
        assert result["metrics"]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_single_agent(self):
        workflow = SequentialWorkflow()
        result = await workflow.execute(
            [StubResearcher()], {"title": "TestCo"}, AgentContextBus()
        )
        assert "market_data" in result

    @pytest.mark.asyncio
    async def test_empty_agents_raises(self):
        workflow = SequentialWorkflow()
        with pytest.raises(ValueError, match="at least one agent"):
            await workflow.execute([], {}, AgentContextBus())

    @pytest.mark.asyncio
    async def test_agent_failure_propagates(self):
        workflow = SequentialWorkflow()
        with pytest.raises(RuntimeError, match="Intentional failure"):
            await workflow.execute(
                [StubResearcher(), FailingAgent()],
                {},
                AgentContextBus(),
            )

    @pytest.mark.asyncio
    async def test_publishes_to_bus(self):
        workflow = SequentialWorkflow()
        bus = AgentContextBus()
        await workflow.execute([StubResearcher()], {"title": "X"}, bus)

        obs = bus.get_observations_for_topic("researcher_output")
        assert len(obs) == 1


# ── ParallelWorkflow ─────────────────────────────────────────────

class TestParallelWorkflow:
    @pytest.mark.asyncio
    async def test_namespace_merge(self):
        workflow = ParallelWorkflow(merge_strategy="namespace")
        agents = [StubResearcher(), StubAnalyst()]
        result = await workflow.execute(agents, {"title": "TestCo"}, AgentContextBus())

        assert "researcher" in result
        assert "analyst" in result
        assert result["analyst"]["metrics"]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_override_merge(self):
        workflow = ParallelWorkflow(merge_strategy="override")
        agents = [StubResearcher(), StubAnalyst()]
        result = await workflow.execute(agents, {"title": "TestCo"}, AgentContextBus())

        # Override merge flattens — analyst's keys appear at top level
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_empty_agents_raises(self):
        workflow = ParallelWorkflow()
        with pytest.raises(ValueError, match="at least one agent"):
            await workflow.execute([], {}, AgentContextBus())

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self):
        workflow = ParallelWorkflow(merge_strategy="namespace")
        agents = [StubResearcher(), FailingAgent()]
        result = await workflow.execute(agents, {}, AgentContextBus())

        assert "researcher" in result
        # Failing agent should not appear (exception caught)
        assert "analyst" not in result


# ── DebateWorkflow ───────────────────────────────────────────────

class TestDebateWorkflow:
    @pytest.mark.asyncio
    async def test_immediate_approval(self):
        workflow = DebateWorkflow(max_rounds=3)
        agents = [
            StubResearcher(),
            StubSynthesizer(),
            StubReviewer(approve_on_round=1),
        ]
        result = await workflow.execute(agents, {}, AgentContextBus())

        assert result["category"] == "B2B SaaS"
        assert result["_debate_metadata"]["approved"] is True
        assert result["_debate_metadata"]["rounds"] == 3

    @pytest.mark.asyncio
    async def test_revision_then_approval(self):
        workflow = DebateWorkflow(max_rounds=3)
        agents = [
            StubSynthesizer(),
            StubReviewer(approve_on_round=2),
        ]
        result = await workflow.execute(agents, {}, AgentContextBus())

        assert result["_debate_metadata"]["approved"] is True
        # Synthesizer was called twice
        assert result["round"] == 2

    @pytest.mark.asyncio
    async def test_non_convergence(self):
        workflow = DebateWorkflow(max_rounds=2)
        agents = [
            StubSynthesizer(),
            StubReviewer(approve_on_round=999),  # Never approve
        ]
        result = await workflow.execute(agents, {}, AgentContextBus())

        assert result["_debate_metadata"]["approved"] is False
        assert len(result["_debate_metadata"]["unresolved_issues"]) > 0

    @pytest.mark.asyncio
    async def test_missing_synthesizer_raises(self):
        workflow = DebateWorkflow()
        with pytest.raises(ValueError, match="at least a Synthesizer and Reviewer"):
            await workflow.execute([StubResearcher()], {}, AgentContextBus())

    @pytest.mark.asyncio
    async def test_missing_reviewer_raises(self):
        workflow = DebateWorkflow()
        with pytest.raises(ValueError, match="SYNTHESIZER and REVIEWER"):
            await workflow.execute(
                [StubResearcher(), StubSynthesizer()], {}, AgentContextBus()
            )

    @pytest.mark.asyncio
    async def test_too_few_agents_raises(self):
        workflow = DebateWorkflow()
        with pytest.raises(ValueError, match="at least a Synthesizer and Reviewer"):
            await workflow.execute([StubSynthesizer()], {}, AgentContextBus())

    @pytest.mark.asyncio
    async def test_review_critique_injected_into_context(self):
        workflow = DebateWorkflow(max_rounds=2)
        agents = [
            StubSynthesizer(),
            StubReviewer(approve_on_round=2),
        ]
        bus = AgentContextBus()
        result = await workflow.execute(agents, {}, bus)

        # First round: no critique in context, second round: critique present
        assert result["revision_applied"] is True
