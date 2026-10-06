"""Financial Intelligence Engine Module — investor-grade financial analysis.

Generates unit economics, projections, scenarios, valuation, and funding analysis
all backed by evidence and assumptions.
"""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from backend.ai.ollama import ollama_adapter
from backend.core.exceptions import BaseBusinessException
from backend.modules.financial_intelligence.schemas import (
    FinancialIntelligenceOutput, UnitEconomics, ScenarioFinancials, FinancialProjection
)
from backend.modules.evidence.types import EvidenceBackedScore, ConfidenceScore, EvidenceSource, FinancialMetrics
from backend.modules.evidence.collector import search_evidence, gather_financial_evidence
from backend.core.config import settings

logger = logging.getLogger("app.financial_intelligence")


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
- Keep ARR/MRR, projections, scenarios, runway, and valuation internally consistent.
- Do not present hypothetical revenue, customers, valuation, or cash as actual results. Mark assumptions clearly.
- When pricing, paying customers, cash, or unit-economics inputs are missing, label estimates as unvalidated
  and do not invent a revenue forecast or a confident valuation.

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
        if not settings.PIPELINE_FAST_MODE:
            fin_evidence = await gather_financial_evidence(industry, stage)
            evidence.extend(fin_evidence)

        # Gather competitor financial data
        dna = context.get("dna_output") or context.get("dna", {})
        competitors = dna.get("competitor_landscape", [])
        for comp in ([] if settings.PIPELINE_FAST_MODE else competitors[:3]):
            if isinstance(comp, dict) and comp.get("name"):
                comp_ev = await search_evidence(
                    f"{comp['name']} revenue funding valuation", max_results=2
                )
                evidence.extend(comp_ev)

        # Fast mode skips optional evidence collection, not the financial analysis itself.
        output = await self._generate_financials(context, evidence)
        return output.model_dump()

    async def _generate_financials(
        self, context: dict[str, Any], evidence: list[EvidenceSource]
    ) -> FinancialIntelligenceOutput:
        """Generate comprehensive financial analysis."""
        features = context.get("features_output") or context.get("features", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('name', 'Feature')}: effort={f.get('effort_estimate', 'M')}, value={f.get('business_value', 5)}/10"
            for f in feature_list[:10] if isinstance(f, dict)
        )

        team = context.get("team_output") or context.get("team", {})
        roles = team.get("org_chart") or team.get("roles", [])
        team_summary = ", ".join(
            r.get("title", "Role") for r in roles[:6] if isinstance(r, dict)
        ) or "Not specified"

        cost = context.get("cost_output") or context.get("cost", {})
        monthly_payroll = float(cost.get("total_monthly_payroll_usd", 0) or 0)
        operating_costs = sum(
            float(item.get("monthly_usd", 0) or 0)
            for item in cost.get("operational_costs", [])
            if isinstance(item, dict) and item.get("category") != "SALARIES"
        )
        monthly_burn = max(
            float(cost.get("monthly_burn_usd", 0) or 0),
            monthly_payroll + operating_costs,
        )

        dna = context.get("dna_output") or context.get("dna", {})
        competitors = dna.get("competitor_landscape", [])
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

        try:
            result = await ollama_adapter.generate(
                prompt=prompt,
                schema=FinancialIntelligenceOutput,
                system_instruction="You are a Senior Financial Analyst producing investor-grade financial analysis with evidence-backed assumptions.",
            )
        except BaseBusinessException as exc:
            if exc.code != "OLLAMA_VALIDATION_ERROR":
                raise
            logger.warning(
                "Financial intelligence output did not match its schema; returning a conservative, "
                "explicitly unvalidated baseline instead."
            )
            return self._fallback_output(evidence, monthly_burn, context)

        if isinstance(result, FinancialIntelligenceOutput):
            result.evidence = evidence[:15]
            uncertainty_text = " ".join([
                result.explanation,
                *result.key_assumptions,
                *result.metrics.assumptions,
            ]).lower()
            if any(marker in uncertainty_text for marker in (
                "fallback", "requires actual financial data", "not validated", "unvalidated baseline",
            )):
                return self._fallback_output(evidence, monthly_burn, context)
            return self._complete_unit_economics(result, context, monthly_burn)

        return self._fallback_output(evidence, monthly_burn, context)

    @staticmethod
    def _estimate_unit_economics(context: dict[str, Any]) -> tuple[UnitEconomics, list[str]]:
        """Calculate a clearly labeled planning estimate when company metrics are unavailable."""
        dna = context.get("dna_output") or context.get("dna") or {}
        customer_type = str(dna.get("customer_type", "")).upper() if isinstance(dna, dict) else ""
        business_model = str(dna.get("business_model", "")).lower() if isinstance(dna, dict) else ""
        context_text = " ".join((
            str(context.get("industry", "")),
            str(context.get("product_description", "")),
            str(context.get("description", "")),
            business_model,
        )).lower()

        if customer_type == "B2B":
            monthly_revenue_per_customer = 500.0
            cac = 750.0
            gross_margin = 80.0
            monthly_churn = 3.0
            segment_assumption = "B2B subscription planning profile: $500 monthly revenue per customer."
        elif customer_type == "B2C":
            monthly_revenue_per_customer = 25.0
            cac = 150.0
            gross_margin = 75.0
            monthly_churn = 5.0
            segment_assumption = "B2C subscription planning profile: $25 monthly revenue per customer."
        else:
            monthly_revenue_per_customer = 100.0
            cac = 300.0
            gross_margin = 70.0
            monthly_churn = 4.0
            segment_assumption = "General subscription planning profile: $100 monthly revenue per customer."

        if any(term in context_text for term in ("marketplace", "commission", "transaction fee")):
            gross_margin = min(gross_margin, 60.0)
            segment_assumption += " Marketplace delivery costs reduce assumed gross margin to 60%."
        elif any(term in context_text for term in ("consulting", "agency", "professional service")):
            gross_margin = min(gross_margin, 55.0)
            segment_assumption += " Service delivery labor reduces assumed gross margin to 55%."

        ltv = monthly_revenue_per_customer * (gross_margin / 100) / (monthly_churn / 100)
        contribution_margin = max(gross_margin - 10.0, 0.0)
        assumptions = [
            segment_assumption,
            f"Estimated CAC is ${cac:,.0f} per acquired customer; replace with actual channel spend and conversion data.",
            f"Monthly churn is assumed at {monthly_churn:.0f}%; LTV uses monthly revenue × gross margin ÷ monthly churn.",
            "These are illustrative planning estimates, not measured company results or verified market benchmarks.",
        ]
        return UnitEconomics(
            cac=cac,
            ltv=round(ltv, 2),
            ltv_cac_ratio=round(ltv / cac, 2),
            payback_period_months=max(
                1,
                ceil(cac / (monthly_revenue_per_customer * gross_margin / 100)),
            ),
            gross_margin_percent=gross_margin,
            net_margin_percent=-20.0,
            contribution_margin_percent=contribution_margin,
            churn_rate_percent=monthly_churn,
            expansion_rate_percent=2.0,
            assumptions=assumptions,
        ), assumptions

    @classmethod
    def _complete_unit_economics(
        cls,
        output: FinancialIntelligenceOutput,
        context: dict[str, Any],
        monthly_burn: float,
    ) -> FinancialIntelligenceOutput:
        """Fill missing unit metrics from explicit, visible planning assumptions."""
        estimate, assumptions = cls._estimate_unit_economics(context)
        current = output.unit_economics
        used_estimates = False
        for field in (
            "cac", "ltv", "ltv_cac_ratio", "payback_period_months",
            "gross_margin_percent", "net_margin_percent",
            "contribution_margin_percent", "churn_rate_percent",
            "expansion_rate_percent",
        ):
            if getattr(current, field) == 0:
                setattr(current, field, getattr(estimate, field))
                used_estimates = True
        if used_estimates:
            current.assumptions = list(dict.fromkeys([*current.assumptions, *assumptions]))

        metrics = output.metrics
        for field in (
            "cac", "ltv", "ltv_cac_ratio", "payback_period_months",
            "gross_margin_percent",
        ):
            if getattr(metrics, field) == 0:
                metrics_value = getattr(current, field)
                setattr(metrics, field, metrics_value)
        if metrics.burn_rate == 0 and monthly_burn > 0:
            metrics.burn_rate = monthly_burn
        if used_estimates:
            metrics.assumptions = list(dict.fromkeys([*metrics.assumptions, *assumptions]))
        return output

    def _fallback_output(
        self,
        evidence: list[EvidenceSource],
        monthly_burn: float,
        context: dict[str, Any] | None = None,
    ) -> FinancialIntelligenceOutput:
        """Return an unvalidated baseline with explicit, nonzero unit-economics assumptions."""
        monthly_burn = max(float(monthly_burn or 0), 0)
        unit_economics, unit_assumptions = self._estimate_unit_economics(context or {})
        assumptions = [
            "No validated customer, pricing, cash-balance, or unit-economics data was supplied.",
            "Revenue and valuation are left at zero; this is an unvalidated baseline, not a forecast.",
            *unit_assumptions,
        ]
        return FinancialIntelligenceOutput(
            metrics=FinancialMetrics(
                arr=0.0, mrr=0.0, gross_margin_percent=unit_economics.gross_margin_percent,
                cac=unit_economics.cac, ltv=unit_economics.ltv,
                ltv_cac_ratio=unit_economics.ltv_cac_ratio,
                burn_rate=monthly_burn, burn_multiple=0.0,
                payback_period_months=unit_economics.payback_period_months,
                cash_runway_months=0,
                assumptions=assumptions,
                evidence=evidence[:5],
            ),
            unit_economics=UnitEconomics(
                **unit_economics.model_dump(exclude={"evidence"}),
                evidence=evidence[:3],
            ),
            projections=[
                FinancialProjection(
                    period="Month 1", revenue=0, costs=monthly_burn,
                    profit=-monthly_burn, cash_balance=0,
                    customers=0, arr=0, mrr=0,
                )
            ],
            scenarios=[
                ScenarioFinancials(
                    scenario_name="Unvalidated baseline", probability=1.0,
                    year1_revenue=0, year3_revenue=0,
                    break_even_month=None, total_funding_required=monthly_burn * 12,
                    runway_months=0, valuation_estimate=0,
                )
            ],
            funding_requirements={
                "current_round": "Not determined",
                "amount": round(monthly_burn * 12),
                "basis": "Twelve months of estimated operating burn; validate scope, cash, and runway before fundraising.",
            },
            valuation={
                "method": "Not estimable from supplied data",
                "estimated_value": 0,
                "confidence": "INSUFFICIENT_DATA",
            },
            key_assumptions=assumptions,
            financial_risks=["Revenue, pricing, cash balance, and customer acquisition costs have not been validated."],
            recommendations=["Collect paid-pilot, pricing, cash, and customer-acquisition data before presenting a forecast or valuation."],
            evidence=evidence[:10],
            confidence=ConfidenceScore(
                score=0.0,
                evidence=evidence[:5],
                missing_information=["Validated pricing", "Paying-customer pipeline", "Cash balance", "Customer acquisition costs"],
                assumptions=assumptions,
            ),
            explanation="Unvalidated baseline only; no revenue forecast or valuation is implied.",
        )
