"""Multi-Agent Decision Pipeline — runs all agents and collects Judge verdict.

Orchestrates the 8 specialized agents and Judge to produce a consensus-driven,
evidence-backed decision with full explainability.
"""

from __future__ import annotations

from typing import Any
import asyncio

from backend.modules.evidence.types import EvidenceSource
from backend.modules.evidence.multi_agent import Judge
from backend.modules.evidence.agents.market_analyst import MarketAnalystAgent
from backend.modules.evidence.agents.product_strategist import ProductStrategistAgent
from backend.modules.evidence.agents.technical_architect import TechnicalArchitectAgent
from backend.modules.evidence.agents.financial_analyst import FinancialAnalystAgent
from backend.modules.evidence.agents.gtm_strategist import GTMStrategistAgent
from backend.modules.evidence.agents.risk_analyst import RiskAnalystAgent
from backend.modules.evidence.agents.devils_advocate import DevilsAdvocateAgent

# All specialized agents (Judge is separate — it reviews their output)
SPECIALIZED_AGENTS = [
    MarketAnalystAgent(),
    ProductStrategistAgent(),
    TechnicalArchitectAgent(),
    FinancialAnalystAgent(),
    GTMStrategistAgent(),
    RiskAnalystAgent(),
    DevilsAdvocateAgent(),
]

JUDGE = Judge()


async def run_decision_pipeline(
    context: dict[str, Any],
    evidence: list[EvidenceSource] | None = None,
    stages: list[str] | None = None,
) -> dict[str, Any]:
    """Run all agents in parallel, then have the Judge deliberate.

    Args:
        context: Analysis context (industry, product, features, etc.)
        evidence: Pre-gathered evidence to share with agents
        stages: Optional list of agent stages to run. None = all agents.

    Returns:
        Dictionary with all agent opinions and Judge verdict.
    """
    evidence = evidence or []
    agents = SPECIALIZED_AGENTS

    # Filter agents if specific stages requested
    if stages:
        agents = [a for a in agents if a.role in stages]

    # Run all agents in parallel
    opinion_tasks = [agent.assess(context, evidence) for agent in agents]
    opinions = await asyncio.gather(*opinion_tasks, return_exceptions=True)

    # Filter out exceptions
    valid_opinions = []
    for i, result in enumerate(opinions):
        if isinstance(result, Exception):
            # Create a fallback opinion for failed agents
            from backend.modules.evidence.multi_agent import AgentOpinion
            from backend.modules.evidence.types import ConfidenceScore
            valid_opinions.append(AgentOpinion(
                agent_role=agents[i].role,
                assessment=f"Agent failed: {str(result)[:200]}",
                key_findings=[f"Error: {str(result)[:100]}"],
                confidence=ConfidenceScore(score=10.0, evidence=evidence[:3]),
            ))
        else:
            valid_opinions.append(result)

    # Judge deliberates on all opinions
    verdict = await JUDGE.deliberate(valid_opinions)

    return {
        "opinions": [op.model_dump() for op in valid_opinions],
        "verdict": verdict.model_dump(),
        "agent_count": len(valid_opinions),
        "evidence_used": len(evidence),
    }
