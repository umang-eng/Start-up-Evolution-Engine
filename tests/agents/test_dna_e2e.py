"""Unit tests for DNA stage end-to-end with AgentModule.

Tests use mocked LLM responses (fixtures, not live network calls).
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from backend.agents.types import AgentRole, AgentBudget, ResearchFindings, AnalysisReport, ReviewCritique
from backend.agents.context_bus import AgentContextBus
from backend.agents.agents.researcher import ResearcherAgent
from backend.agents.agents.analyst import AnalystAgent
from backend.agents.agents.reviewer import ReviewerAgent
from backend.agents.workflows import SequentialWorkflow


# ── Fixture data ──────────────────────────────────────────────────

FIXTURE_DNA_OUTPUT = {
    "category": "B2B SaaS",
    "customer_type": "B2B",
    "market_type": "Existing niche",
    "business_model": "Subscription-based SaaS",
    "revenue_streams": ["Monthly SaaS", "Enterprise licensing"],
    "value_proposition": "AI-powered workflow automation for mid-market companies",
    "usp": "First AI agent mesh for startup analysis",
    "target_segments": ["Mid-market SaaS companies", "Enterprise innovation teams"],
    "scores": {
        "innovation": 82,
        "scalability": 75,
        "complexity": 60,
        "market_opportunity": 78,
        "risk_factor": 35,
        "competition": 55,
    },
    "executive_summary": "Strong B2B SaaS opportunity with solid market fit and innovation scores.",
    "strategic_recommendations": [
        "Focus on mid-market first",
        "Build enterprise features early",
        "Establish AI differentiation",
    ],
    "confidence_score": 0.78,
    "confidence_rationale": "Based on market analysis and competitive landscape",
}


# ── ResearcherAgent tests ────────────────────────────────────────

class TestResearcherAgent:
    @pytest.mark.asyncio
    async def test_returns_research_findings(self):
        agent = ResearcherAgent(budget=AgentBudget(max_tool_calls=5))
        bus = AgentContextBus()

        with patch.object(agent, "use_tool") as mock_tool:
            mock_tool.return_value = MagicMock(
                ok=True,
                data={"formatted_market": "[DATA]test[/DATA]", "responses": []},
            )
            result = await agent.run(
                {"project_id": "test-123", "industry": "tech", "enable_web_research": True},
                bus,
            )
            assert isinstance(result, ResearchFindings)
            assert result.market_data is not None

    @pytest.mark.asyncio
    async def test_handles_tool_failure(self):
        from backend.agents.types import ToolCallResult

        agent = ResearcherAgent(budget=AgentBudget(max_tool_calls=5))
        bus = AgentContextBus()

        fail_result = ToolCallResult(tool_name="web_search", ok=False, error="API down")

        with patch.object(agent, "use_tool") as mock_tool:
            mock_tool.return_value = fail_result
            result = await agent.run(
                {"project_id": "test-123", "enable_web_research": True},
                bus,
            )
            assert isinstance(result, ResearchFindings)
            assert len(result.tool_errors) > 0
            assert result.tool_errors[0].ok is False


# ── AnalystAgent tests ───────────────────────────────────────────

class TestAnalystAgent:
    @pytest.mark.asyncio
    async def test_analyzes_dna_scores(self):
        agent = AnalystAgent(budget=AgentBudget(max_tool_calls=3))
        bus = AgentContextBus()

        context = {
            "dna": {
                "scores": {
                    "innovation": 80,
                    "scalability": 70,
                    "market_opportunity": 75,
                    "risk_factor": 30,
                }
            }
        }

        result = await agent.run(context, bus)
        assert isinstance(result, AnalysisReport)
        assert "innovation" in result.metrics
        assert result.metrics["innovation"] == 0.8
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_empty_context(self):
        agent = AnalystAgent(budget=AgentBudget(max_tool_calls=3))
        bus = AgentContextBus()
        result = await agent.run({}, bus)
        assert isinstance(result, AnalysisReport)
        assert result.confidence >= 0


# ── ReviewerAgent tests ──────────────────────────────────────────

class TestReviewerAgent:
    @pytest.mark.asyncio
    async def test_approves_valid_output(self):
        agent = ReviewerAgent()
        bus = AgentContextBus()

        # Publish a valid synthesis
        from pydantic import BaseModel

        class ValidSynth(BaseModel):
            data: dict

        await bus.publish(
            AgentRole.SYNTHESIZER,
            MagicMock(
                topic="synthesis_complete",
                producer=AgentRole.SYNTHESIZER,
                data=ValidSynth(data=FIXTURE_DNA_OUTPUT),
            ),
        )

        result = await agent.run({}, bus)
        assert isinstance(result, ReviewCritique)
        assert result.approved is True
        assert result.severity == "none"

    @pytest.mark.asyncio
    async def test_rejects_empty_output(self):
        agent = ReviewerAgent()
        bus = AgentContextBus()

        # Publish empty synthesis
        from pydantic import BaseModel

        class EmptySynth(BaseModel):
            data: dict

        await bus.publish(
            AgentRole.SYNTHESIZER,
            MagicMock(
                topic="synthesis_complete",
                producer=AgentRole.SYNTHESIZER,
                data=EmptySynth(data={}),
            ),
        )

        result = await agent.run({}, bus)
        assert result.approved is False
        assert result.severity == "blocking"

    @pytest.mark.asyncio
    async def test_rejects_missing_lists(self):
        agent = ReviewerAgent()
        bus = AgentContextBus()

        output = FIXTURE_DNA_OUTPUT.copy()
        output["revenue_streams"] = []
        output["target_segments"] = []

        from pydantic import BaseModel

        class PartialSynth(BaseModel):
            data: dict

        await bus.publish(
            AgentRole.SYNTHESIZER,
            MagicMock(
                topic="synthesis_complete",
                producer=AgentRole.SYNTHESIZER,
                data=PartialSynth(data=output),
            ),
        )

        result = await agent.run({}, bus)
        assert result.approved is False
        assert result.severity == "blocking"


# ── SequentialWorkflow integration ───────────────────────────────

class TestDNAWorkflowIntegration:
    @pytest.mark.asyncio
    async def test_sequential_dna_workflow(self):
        """Test a full sequential DNA workflow with mocked agents."""
        researcher = ResearcherAgent(budget=AgentBudget(max_tool_calls=5))
        reviewer = ReviewerAgent()

        # Mock researcher tool calls
        with patch.object(researcher, "use_tool") as mock_tool:
            mock_tool.return_value = MagicMock(
                ok=True,
                data={"formatted_market": "[DATA]test[/DATA]", "responses": []},
            )

            # Run researcher + reviewer
            workflow = SequentialWorkflow()
            agents = [researcher, reviewer]
            bus = AgentContextBus()

            result = await workflow.execute(
                agents,
                {"project_id": "test-123", "industry": "tech"},
                bus,
            )

            # Reviewer should have run (but may not approve without synthesis)
            assert isinstance(result, dict)
