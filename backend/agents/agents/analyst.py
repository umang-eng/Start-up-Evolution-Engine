"""AnalystAgent — Analyzes data, computes metrics, identifies patterns.

This agent receives research findings and context data, computes analytical
metrics, and produces an AnalysisReport for the Synthesizer.
"""

from __future__ import annotations

from typing import Any

from backend.agents.base import BaseAgent
from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole, AnalysisReport, ResearchFindings


class AnalystAgent(BaseAgent):
    """Analyzes research data and computes metrics for downstream synthesis."""

    role = AgentRole.ANALYST
    tools = ["calculation"]

    SYSTEM_INSTRUCTION = (
        "You are a senior business analyst. Analyze the provided data, "
        "compute relevant metrics, and identify key patterns."
    )

    async def run(
        self,
        context: dict[str, Any],
        bus: AgentContextBus,
    ) -> AnalysisReport:
        """Analyze data from context and any available research findings."""
        # Try to get research findings from bus
        research_data: dict[str, Any] = {}
        try:
            obs = await self.wait_for_observation(bus, "researcher_output", timeout_s=5.0)
            if isinstance(obs.data, ResearchFindings):
                research_data = obs.data.market_data
            elif hasattr(obs.data, "data"):
                research_data = getattr(obs.data, "data", {})
        except Exception:
            pass

        # Merge context with research data
        dna = context.get("dna", {})
        scores = dna.get("scores", {})

        metrics: dict[str, float] = {}
        patterns: list[str] = []

        # Compute metrics from DNA scores if available
        if scores:
            for key in ["innovation", "scalability", "complexity", "market_opportunity", "risk_factor", "competition"]:
                if key in scores:
                    metrics[key] = float(scores[key]) / 100.0

        # Compute aggregate metrics
        if metrics:
            metrics["average_score"] = sum(metrics.values()) / len(metrics)
            metrics["risk_adjusted_opportunity"] = (
                metrics.get("market_opportunity", 0.5) * (1 - metrics.get("risk_factor", 0.5))
            )

        # Identify patterns from research data
        if research_data:
            if "formatted_market" in research_data:
                patterns.append("Market data available from web research")
            if "formatted_funding" in research_data:
                patterns.append("Funding intelligence available")

        # Use calculation tool for threat severity if SWOT data present
        swot = context.get("swot", {})
        threats = swot.get("threats", [])
        if threats:
            calc_result = await self.use_tool(
                "calculation",
                bus,
                calc_type="health_indicators",
                inputs={
                    "dna": dna,
                    "features": context.get("features", {}),
                    "roadmap": context.get("roadmap", {}),
                    "swot": swot,
                    "cost": context.get("cost", {}),
                },
            )
            if calc_result.ok and calc_result.data:
                for k, v in calc_result.data.items():
                    if isinstance(v, (int, float)):
                        metrics[k] = float(v)
                patterns.append("Health indicators computed")

        # Compute confidence
        confidence = 0.5
        if scores:
            confidence = min(1.0, 0.3 + len(scores) * 0.1)
        if research_data:
            confidence = min(1.0, confidence + 0.2)

        return AnalysisReport(
            metrics=metrics,
            patterns=patterns,
            confidence=confidence,
        )
