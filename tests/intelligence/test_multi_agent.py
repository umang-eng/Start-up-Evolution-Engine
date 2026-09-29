"""Tests for multi-agent decision system."""

import pytest
import asyncio
from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource
)
from backend.modules.evidence.multi_agent import (
    AgentOpinion, JudgeVerdict, Judge, SpecializedAgent
)
from backend.modules.evidence.agents.market_analyst import MarketAnalystAgent
from backend.modules.evidence.agents.product_strategist import ProductStrategistAgent
from backend.modules.evidence.agents.technical_architect import TechnicalArchitectAgent
from backend.modules.evidence.agents.financial_analyst import FinancialAnalystAgent
from backend.modules.evidence.agents.gtm_strategist import GTMStrategistAgent
from backend.modules.evidence.agents.risk_analyst import RiskAnalystAgent
from backend.modules.evidence.agents.devils_advocate import DevilsAdvocateAgent
from backend.modules.evidence.agents.judge import InvestmentCommitteeJudgeAgent


class TestAgentOpinion:
    def test_create_opinion(self):
        opinion = AgentOpinion(
            agent_role="Market Analyst",
            assessment="Market is growing at 15% CAGR",
            key_findings=["Market size $50B", "Growth rate 15%"],
            risks_identified=["Competition increasing"],
            recommendations=["Enter market now"],
            confidence=ConfidenceScore(score=75.0),
        )
        assert opinion.agent_role == "Market Analyst"
        assert len(opinion.key_findings) == 2
        assert opinion.confidence.score == 75.0


class TestJudgeVerdict:
    def test_create_verdict(self):
        verdict = JudgeVerdict(
            final_assessment="Strong investment opportunity",
            agreements=["Market is large"],
            conflicts=["Timing is uncertain"],
            conflict_resolutions=["Lean toward optimistic timing"],
            overall_confidence=ConfidenceScore(score=70.0),
            key_risks=["Competitive response"],
            recommendations=["Proceed with caution"],
        )
        assert verdict.final_assessment == "Strong investment opportunity"
        assert len(verdict.agreements) == 1
        assert len(verdict.conflicts) == 1


class TestJudge:
    @pytest.mark.asyncio
    async def test_judge_deliberate_single_opinion(self):
        judge = Judge()
        opinion = AgentOpinion(
            agent_role="Market Analyst",
            assessment="Market opportunity is strong",
            key_findings=["Large TAM"],
            confidence=ConfidenceScore(score=75.0),
        )
        verdict = await judge.deliberate([opinion])
        assert isinstance(verdict, JudgeVerdict)
        assert len(verdict.agreements) >= 0

    @pytest.mark.asyncio
    async def test_judge_deliberate_multiple_opinions(self):
        judge = Judge()
        opinions = [
            AgentOpinion(
                agent_role="Market Analyst",
                assessment="Market is growing rapidly",
                key_findings=["Strong growth signals"],
                confidence=ConfidenceScore(score=80.0),
            ),
            AgentOpinion(
                agent_role="Financial Analyst",
                assessment="Unit economics are promising",
                key_findings=["LTV:CAC of 3.5"],
                confidence=ConfidenceScore(score=70.0),
            ),
            AgentOpinion(
                agent_role="Risk Analyst",
                assessment="Risks are manageable",
                key_findings=["Mitigation strategies available"],
                confidence=ConfidenceScore(score=65.0),
            ),
        ]
        verdict = await judge.deliberate(opinions)
        assert isinstance(verdict, JudgeVerdict)
        assert verdict.overall_confidence.score > 0

    @pytest.mark.asyncio
    async def test_judge_conflict_detection(self):
        judge = Judge()
        opinions = [
            AgentOpinion(
                agent_role="Optimist",
                assessment="Market opportunity is HIGH and growing",
                key_findings=["Strong growth"],
                disagreements=[],
                confidence=ConfidenceScore(score=85.0),
            ),
            AgentOpinion(
                agent_role="Pessimist",
                assessment="Market opportunity is LOW and declining",
                key_findings=["Weak demand"],
                disagreements=["Growth is overestimated"],
                confidence=ConfidenceScore(score=60.0),
            ),
        ]
        verdict = await judge.deliberate(opinions)
        assert isinstance(verdict, JudgeVerdict)
        # Should detect some conflict or disagreement
        assert len(verdict.dissenting_views) >= 0


class TestSpecializedAgents:
    @pytest.mark.asyncio
    async def test_market_analyst(self):
        agent = MarketAnalystAgent()
        context = {
            "industry": "AI/ML",
            "product_description": "AI-powered analytics platform",
            "target_market": "Enterprise",
        }
        evidence = [
            EvidenceSource(source_name="Gartner", source_type="WEB_SEARCH",
                          snippet="AI market growing at 35% CAGR"),
        ]
        opinion = await agent.assess(context, evidence)
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Market Analyst"
        assert len(opinion.key_findings) > 0
        assert opinion.confidence.score > 0

    @pytest.mark.asyncio
    async def test_product_strategist(self):
        agent = ProductStrategistAgent()
        context = {
            "industry": "SaaS",
            "product_description": "Project management tool",
            "target_market": "SMBs",
            "features": [{"name": "Task Management", "effort_estimate": "M"}],
        }
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Product Strategist"

    @pytest.mark.asyncio
    async def test_technical_architect(self):
        agent = TechnicalArchitectAgent()
        context = {
            "industry": "Cloud",
            "product_description": "Cloud infrastructure platform",
            "features": [{"name": "Auto-scaling", "effort_estimate": "L"}],
        }
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Technical Architect"

    @pytest.mark.asyncio
    async def test_financial_analyst(self):
        agent = FinancialAnalystAgent()
        context = {
            "industry": "FinTech",
            "product_description": "Digital payments platform",
            "cost_output": {"total_monthly_payroll_usd": 25000},
        }
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Financial Analyst"

    @pytest.mark.asyncio
    async def test_gtm_strategist(self):
        agent = GTMStrategistAgent()
        context = {
            "industry": "E-commerce",
            "product_description": "Online marketplace",
            "target_market": "Consumers",
        }
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "GTM Strategist"

    @pytest.mark.asyncio
    async def test_risk_analyst(self):
        agent = RiskAnalystAgent()
        context = {
            "industry": "HealthTech",
            "product_description": "Telemedicine platform",
        }
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Risk Analyst"

    @pytest.mark.asyncio
    async def test_devils_advocate(self):
        agent = DevilsAdvocateAgent()
        context = {
            "industry": "EdTech",
            "product_description": "Online learning platform",
            "features": [],
        }
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Devil's Advocate"

    @pytest.mark.asyncio
    async def test_judge_agent(self):
        agent = InvestmentCommitteeJudgeAgent()
        context = {"industry": "AI"}
        opinion = await agent.assess(context, [])
        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_role == "Investment Committee Judge"


class TestDecisionPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_runs_all_agents(self):
        from backend.modules.evidence.pipeline import run_decision_pipeline
        context = {
            "industry": "SaaS",
            "product_description": "CRM platform",
            "target_market": "SMBs",
            "features": [{"name": "Contact Management", "effort_estimate": "M"}],
            "cost_output": {"total_monthly_payroll_usd": 20000},
        }
        result = await run_decision_pipeline(context, evidence=[])
        assert "opinions" in result
        assert "verdict" in result
        assert result["agent_count"] == 7  # All specialized agents
        assert len(result["opinions"]) == 7

    @pytest.mark.asyncio
    async def test_pipeline_with_selected_stages(self):
        from backend.modules.evidence.pipeline import run_decision_pipeline
        context = {
            "industry": "AI",
            "product_description": "AI assistant",
            "target_market": "Enterprise",
        }
        result = await run_decision_pipeline(
            context, evidence=[],
            stages=["Market Analyst", "Financial Analyst"]
        )
        assert result["agent_count"] == 2
