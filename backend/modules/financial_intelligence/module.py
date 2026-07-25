"""Financial Intelligence Engine Module — investor-grade financial analysis.

Generates unit economics, projections, scenarios, valuation, and funding analysis
all backed by evidence and assumptions.
"""

from __future__ import annotations

from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.modules.financial_intelligence.schemas import (
    FinancialIntelligenceOutput, UnitEconomics, ScenarioFinancials, FinancialProjection
)
from backend.modules.evidence.types import EvidenceBackedScore, ConfidenceScore, EvidenceSource, FinancialMetrics
from backend.modules.evidence.collector import search_evidence, gather_financial_evidence


FINANCIAL_PROMPT = """You are a Senior Financial Analyst producing investor-grade financial analysis.

## Startup Context
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Stage: {stage}
- Features: {features_summary}
- Team: {team_summary}
- Monthly Burn: ${monthly_burn:,.0f}
- Monthly Payroll: ${monthly_payroll:,.0f}

## Competitors
{competitors_text}

## Evidence (market data, benchmarks)
{evidence_text}

## Required Analysis

### 1. Core Metrics
- ARR, MRR (with growth assumptions)
- Gross Margin (based on industry benchmarks)
- CAC (with channel breakdown)
- LTV (with retention assumptions)
- Burn Rate (current and projected)
- Burn Multiple
- Payback Period
- Cash Runway
- Break-even month

### 2. Unit Economics
- CAC by channel (organic, paid, referral)
- LTV with churn assumptions
- LTV:CAC ratio
- Gross margin per unit
- Contribution margin
- Expansion revenue rate

### 3. Financial Projections (Monthly for Year 1, Quarterly for Years 2-3)
For each period: revenue, costs, profit, cash balance, customers, ARR, MRR

### 4. Three Scenarios
- **Best Case** (20% probability): Everything goes right
- **Base Case** (60% probability): Reasonable expectations
- **Worst Case** (20% probability): Significant challenges

For each scenario: revenue, break-even month, funding required, runway, valuation

### 5. Funding Analysis
- Current round requirements
- Use of proceeds breakdown
- Expected valuation range
- Investor return projections

### 6. Valuation
- Revenue multiple approach
- Comparable company analysis
- Pre-money vs post-money

## Important
- All calculations must reference specific assumptions
- Use industry benchmarks from evidence where available
- Flag where data is estimated vs verified
- Be conservative in projections

Return valid FinancialIntelligenceOutput JSON."""


class FinancialIntelligenceModule:
    """Generates investor-grade financial analysis with evidence-backed assumptions."""

    stage_name = "financial_intelligence"
    input_stages = ["dna", "features", "roadmap", "team", "cost", "blueprint"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []
        industry = context.get("industry", "technology")
        stage = context.get("stage", "pre-seed")

        # Gather financial benchmark evidence
        fin_evidence = await gather_financial_evidence(industry, stage)
        evidence.extend(fin_evidence)

        # Gather competitor financial data
        competitors = context.get("dna_output", {}).get("competitor_landscape", [])
        for comp in competitors[:3]:
            if isinstance(comp, dict) and comp.get("name"):
                comp_ev = await search_evidence(
                    f"{comp['name']} revenue funding valuation", max_results=2
                )
                evidence.extend(comp_ev)

        # Generate financial intelligence
        output = await self._generate_financials(context, evidence)
        return output.model_dump()

    async def _generate_financials(
        self, context: dict[str, Any], evidence: list[EvidenceSource]
    ) -> FinancialIntelligenceOutput:
        """Generate comprehensive financial analysis."""
        features = context.get("features_output", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('name', 'Feature')}: effort={f.get('effort_estimate', 'M')}, value={f.get('business_value', 5)}/10"
            for f in feature_list[:10] if isinstance(f, dict)
        )

        team = context.get("team_output", {})
        roles = team.get("roles", [])
        team_summary = ", ".join(
            r.get("title", "Role") for r in roles[:6] if isinstance(r, dict)
        ) or "Not specified"

        cost = context.get("cost_output", {})
        monthly_burn = cost.get("total_monthly_payroll_usd", 15000)
        monthly_payroll = cost.get("total_monthly_payroll_usd", 15000)

        competitors = context.get("dna_output", {}).get("competitor_landscape", [])
        competitors_text = "\n".join(
            f"- {c.get('name', 'Unknown')}: {c.get('description', '')[:60]}"
            for c in competitors[:5] if isinstance(c, dict)
        ) or "No competitor data"

        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:120]}"
            for e in evidence[:20]
        )

        prompt = FINANCIAL_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            stage=context.get("stage", "pre-seed"),
            features_summary=features_summary,
            team_summary=team_summary,
            monthly_burn=monthly_burn,
            monthly_payroll=monthly_payroll,
            competitors_text=competitors_text,
            evidence_text=evidence_text,
        )

        result = await gemini_adapter.generate(
            prompt=prompt,
            schema=FinancialIntelligenceOutput,
            system_instruction="You are a Senior Financial Analyst producing investor-grade financial analysis with evidence-backed assumptions.",
        )

        if isinstance(result, FinancialIntelligenceOutput):
            result.evidence = evidence[:15]
            return result

        return self._fallback_output(evidence, monthly_burn)

    def _fallback_output(self, evidence: list[EvidenceSource], monthly_burn: float) -> FinancialIntelligenceOutput:
        """Fallback financial analysis."""
        return FinancialIntelligenceOutput(
            metrics=FinancialMetrics(
                arr=0.0, mrr=0.0, gross_margin_percent=70.0,
                cac=100.0, ltv=300.0, ltv_cac_ratio=3.0,
                burn_rate=monthly_burn, burn_multiple=2.0,
                payback_period_months=12, cash_runway_months=18,
                assumptions=["Fallback values — require actual financial data"],
                evidence=evidence[:5],
            ),
            unit_economics=UnitEconomics(
                cac=100.0, ltv=300.0, ltv_cac_ratio=3.0,
                payback_period_months=12, gross_margin_percent=70.0,
                net_margin_percent=20.0, contribution_margin_percent=60.0,
                churn_rate_percent=5.0, expansion_rate_percent=10.0,
                evidence=evidence[:3],
            ),
            projections=[
                FinancialProjection(
                    period="Month 1", revenue=0, costs=monthly_burn,
                    profit=-monthly_burn, cash_balance=180000,
                    customers=0, arr=0, mrr=0,
                )
            ],
            scenarios=[
                ScenarioFinancials(
                    scenario_name="Base Case", probability=0.6,
                    year1_revenue=120000, year3_revenue=600000,
                    break_even_month=18, total_funding_required=300000,
                    runway_months=18, valuation_estimate=2000000,
                )
            ],
            funding_requirements={
                "current_round": "Pre-Seed",
                "amount": 300000,
                "use_of proceeds": {"product": "60%", "marketing": "25%", "operations": "15%"},
            },
            valuation={
                "method": "Revenue Multiple",
                "estimated_value": 2000000,
                "confidence": "LOW",
            },
            key_assumptions=["Fallback analysis — replace with actual financial modeling"],
            financial_risks=["No actual financial data available"],
            recommendations=["Build detailed financial model with real data"],
            evidence=evidence[:10],
            confidence=ConfidenceScore(score=30.0, evidence=evidence[:5]),
            explanation="Fallback financial analysis — requires actual financial data for accuracy.",
        )
