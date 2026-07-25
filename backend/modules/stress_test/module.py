"""Market Stress Testing Module — simulates future scenarios and their business impact.

Tests multiple negative scenarios and produces mitigation strategies with recovery plans.
"""

from __future__ import annotations

from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.modules.stress_test.schemas import (
    StressTestOutput, StressTestScenario
)
from backend.modules.evidence.types import EvidenceBackedScore, ConfidenceScore, EvidenceSource
from backend.modules.evidence.collector import search_evidence
from backend.modules.evidence.pipeline import run_decision_pipeline


STRESS_TEST_PROMPT = """You are a Risk Simulation Analyst. Perform comprehensive market stress testing.

## Startup Context
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Stage: {stage}
- Features: {features_summary}
- Cost Structure: {cost_summary}

## Competitors
{competitors_text}

## Evidence
{evidence_text}

## Required Scenarios (minimum 8)

Test ALL of these scenarios:

1. **Large Competitor Entry**: A well-funded competitor (Google, Amazon, Microsoft) enters the space
2. **Open-Source Alternative**: A credible open-source alternative is released
3. **Price War**: Competitors slash prices by 50-70%
4. **Regulatory Change**: New regulations restrict the business model
5. **Economic Recession**: Major economic downturn reduces customer spending
6. **Customer Acquisition Doubles**: Unusually rapid growth creates scaling challenges
7. **Customer Acquisition Halves**: Marketing channels become ineffective
8. **Infrastructure Cost Surge**: Cloud/infrastructure costs increase 3x
9. **Funding Freeze**: Venture capital market tightens completely
10. **Key Person Departure**: Critical founder or technical lead leaves

For EACH scenario provide:
- trigger_event: What causes this
- impact: CATASTROPHIC/SEVERE/MODERATE/MINOR/NEGLIGIBLE
- impact_score: 0-10
- probability: 0.0-1.0
- time_to_manifest_months: how fast
- duration_months: how long it lasts
- affected_areas: which business functions
- mitigation_strategy: what to do
- recovery_plan: how to recover
- recovery_time_months: how long recovery takes
- expected_outcome: final state
- early_warning_signs: what to watch for
- pre_positioning: what to do now

## Scoring
- impact_score: 0=no impact, 10=existential threat
- probability: based on historical frequency and current conditions

Return valid StressTestOutput JSON."""


class StressTestModule:
    """Runs comprehensive market stress tests with evidence-backed scenarios."""

    stage_name = "stress_test"
    input_stages = ["dna", "features", "roadmap", "team", "swot", "cost", "blueprint", "competitive_moat"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []

        # Gather stress-test-specific evidence
        industry = context.get("industry", "technology")
        stress_evidence = await search_evidence(
            f"{industry} industry risks threats challenges disruption 2025", max_results=5
        )
        evidence.extend(stress_evidence)

        recession_evidence = await search_evidence(
            f"startup failure rates economic recession impact SaaS 2025", max_results=3
        )
        evidence.extend(recession_evidence)

        # Run multi-agent pipeline for stress test assessment
        decision_context = {**context, "stage": "stress_test"}
        decision_result = await run_decision_pipeline(decision_context, evidence)

        # Generate stress test scenarios
        output = await self._generate_stress_test(context, evidence, decision_result)

        return output.model_dump()

    async def _generate_stress_test(
        self, context: dict[str, Any], evidence: list[EvidenceSource],
        decision_result: dict[str, Any]
    ) -> StressTestOutput:
        """Generate comprehensive stress test scenarios."""
        features = context.get("features_output", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('name', 'Feature')}: {f.get('description', '')[:60]}"
            for f in feature_list[:8] if isinstance(f, dict)
        )

        cost = context.get("cost_output", {})
        cost_summary = (
            f"Monthly burn: ${cost.get('total_monthly_payroll_usd', 0):,.0f}, "
            f"Runway: {cost.get('cash_runway_months', 'unknown')} months"
        )

        competitors = context.get("dna_output", {}).get("competitor_landscape", [])
        competitors_text = "\n".join(
            f"- {c.get('name', 'Unknown')}: {c.get('description', '')[:60]}"
            for c in competitors[:5] if isinstance(c, dict)
        ) or "No competitor data available"

        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:120]}"
            for e in evidence[:15]
        )

        prompt = STRESS_TEST_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            stage=context.get("stage", "pre-seed"),
            features_summary=features_summary,
            cost_summary=cost_summary,
            competitors_text=competitors_text,
            evidence_text=evidence_text,
        )

        result = await gemini_adapter.generate(
            prompt=prompt,
            schema=StressTestOutput,
            system_instruction="You are a Risk Simulation Analyst. Perform comprehensive market stress testing with evidence-backed scenarios.",
        )

        if isinstance(result, StressTestOutput):
            # Add evidence to scenarios
            for scenario in result.scenarios:
                scenario.evidence = evidence[:5]
            result.evidence = evidence[:15]
            return result

        # Fallback
        return self._fallback_output(evidence)

    def _fallback_output(self, evidence: list[EvidenceSource]) -> StressTestOutput:
        """Fallback when LLM fails."""
        fallback_scenario = StressTestScenario(
            scenario_id="fallback-1",
            scenario_name="Market Downturn",
            category="ECONOMIC",
            description="General economic downturn reduces startup funding and customer spending",
            trigger_event="Economic recession",
            impact="SEVERE",
            impact_score=7.0,
            probability=0.3,
            time_to_manifest_months=6,
            duration_months=18,
            affected_areas=["Funding", "Customer Acquisition", "Revenue"],
            mitigation_strategy="Reduce burn rate, focus on profitability, diversify revenue",
            recovery_plan="Build sustainable unit economics, reduce dependency on fundraising",
            recovery_time_months=12,
            expected_outcome="Reduced growth but survival if burn is managed",
            evidence=evidence[:5],
            confidence=ConfidenceScore(score=40.0, evidence=evidence[:3]),
        )

        return StressTestOutput(
            scenarios=[fallback_scenario],
            overall_resilience=EvidenceBackedScore(
                value=50.0, label="Overall Resilience",
                confidence=ConfidenceScore(score=30.0, evidence=evidence[:3]),
                explanation="Fallback assessment — insufficient data for comprehensive stress test"
            ),
            worst_case_scenario="Market Downturn",
            most_likely_scenario="Competitive Pressure",
            risk_score=EvidenceBackedScore(
                value=60.0, label="Risk Score",
                confidence=ConfidenceScore(score=30.0, evidence=evidence[:3]),
                explanation="Moderate risk based on limited evidence"
            ),
            resilience_recommendations=[
                "Conduct comprehensive stress test with more market data",
                "Build financial reserves before scaling",
            ],
            early_warning_system=["Monitor funding market conditions", "Track competitor announcements"],
            evidence=evidence[:10],
            assumptions=["Standard economic cycle patterns"],
            explanation="Fallback stress test — recommend re-running with more comprehensive evidence.",
        )
