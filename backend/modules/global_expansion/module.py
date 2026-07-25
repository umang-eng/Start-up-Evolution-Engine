"""Global Expansion Engine Module — multi-country expansion analysis with evidence.

Generates detailed expansion plans for multiple countries with regulatory,
hiring, pricing, and GTM analysis for each.
"""

from __future__ import annotations

from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.modules.global_expansion.schemas import (
    GlobalExpansionOutput, CountryExpansion, ExpansionWave
)
from backend.modules.evidence.types import ConfidenceScore, EvidenceSource
from backend.modules.evidence.collector import search_evidence, gather_regulatory_evidence


EXPANSION_PROMPT = """You are a Global Expansion Strategist planning international market entry.

## Startup Context
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Stage: {stage}
- Home Market: {home_market}
- Monthly Burn: ${monthly_burn:,.0f}
- Available Capital: ${available_capital:,.00}

## Evidence (market data, regulations)
{evidence_text}

## Required Analysis

### Target Countries (assess 8-12 countries)
For EACH country provide:
1. **Market Size** (USD estimate)
2. **Local Competitors** (2-3 key players)
3. **Regulatory Requirements** (data protection, business registration, industry-specific)
4. **Localization Needs** (language, cultural, payment methods)
5. **Hiring Costs** (average monthly salary for key roles)
6. **Pricing Adjustment** (% vs US pricing — consider purchasing power)
7. **Tax Considerations** (corporate tax, VAT, transfer pricing)
8. **GTM Strategy** (how to enter this market)
9. **Risks** (country-specific risks)
10. **Priority Tier** (TIER_1/TIER_2/TIER_3)

### Expansion Waves
Organize countries into 3 waves:
- **Wave 1** (0-12 months): Easiest, highest ROI markets
- **Wave 2** (12-24 months): Moderate complexity
- **Wave 3** (24-36 months): Most challenging but high potential

For each wave:
- Countries included
- Timeline
- Total investment required
- Expected ARR contribution

### Overall Plan
- Recommended first market and why
- Total expansion investment
- Expected global ARR
- Key global risks
- Strategic recommendations

## Country Selection Criteria
- Market size > $100M
- Regulatory accessibility
- English proficiency or localization cost
- Time zone compatibility
- Existing competitor gaps

Return valid GlobalExpansionOutput JSON."""


class GlobalExpansionModule:
    """Generates comprehensive global expansion analysis with evidence-backed assessments."""

    stage_name = "global_expansion"
    input_stages = ["dna", "features", "roadmap", "cost", "blueprint"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []
        industry = context.get("industry", "technology")

        # Gather global expansion evidence
        expansion_evidence = await search_evidence(
            f"{industry} international expansion global markets 2025", max_results=4
        )
        evidence.extend(expansion_evidence)

        # Gather regulatory evidence for key markets
        target_countries = ["United States", "United Kingdom", "Germany", "Japan", "India", "Brazil"]
        reg_evidence = await gather_regulatory_evidence(industry, target_countries)
        for country_evs in reg_evidence.values():
            evidence.extend(country_evs)

        # Generate expansion plan
        output = await self._generate_expansion(context, evidence)
        return output.model_dump()

    async def _generate_expansion(
        self, context: dict[str, Any], evidence: list[EvidenceSource]
    ) -> GlobalExpansionOutput:
        """Generate global expansion analysis."""
        cost = context.get("cost_output", {})
        monthly_burn = cost.get("total_monthly_payroll_usd", 15000)

        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:120]}"
            for e in evidence[:20]
        ) or "No evidence available"

        prompt = EXPANSION_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            stage=context.get("stage", "pre-seed"),
            home_market="United States",
            monthly_burn=monthly_burn,
            available_capital=300000,
            evidence_text=evidence_text,
        )

        result = await gemini_adapter.generate(
            prompt=prompt,
            schema=GlobalExpansionOutput,
            system_instruction="You are a Global Expansion Strategist planning international market entry.",
        )

        if isinstance(result, GlobalExpansionOutput):
            result.evidence = evidence[:15]
            return result

        return self._fallback_output(evidence)

    def _fallback_output(self, evidence: list[EvidenceSource]) -> GlobalExpansionOutput:
        """Fallback expansion plan."""
        wave1 = ExpansionWave(
            wave_number=1,
            wave_name="Quick Wins",
            countries=[
                CountryExpansion(
                    country="United Kingdom", country_code="GB", priority="TIER_1",
                    market_size_usd=500000000, local_competitors=["Local Corp", "UK Tech Ltd"],
                    regulatory_requirements=["Companies House registration", "GDPR compliance"],
                    localization_needs=["British English", "GBP pricing"],
                    hiring_costs_monthly=6000, pricing_adjustment_percent=0,
                    tax_considerations=["20% corporation tax", "VAT registration"],
                    gtm_strategy="Direct sales with local partnerships",
                    risks=["Post-Brexit regulatory divergence"],
                    confidence=ConfidenceScore(score=55.0, evidence=evidence[:3]),
                ),
                CountryExpansion(
                    country="Canada", country_code="CA", priority="TIER_1",
                    market_size_usd=300000000, local_competitors=["Canadian Tech Co"],
                    regulatory_requirements=["Federal incorporation", "PIPEDA compliance"],
                    localization_needs=["French for Quebec", "CAD pricing"],
                    hiring_costs_monthly=5500, pricing_adjustment_percent=-5,
                    tax_considerations=["15% federal tax", "Provincial taxes"],
                    gtm_strategy="Leverage US market adjacency",
                    risks=["Smaller market size"],
                    confidence=ConfidenceScore(score=60.0, evidence=evidence[:3]),
                ),
            ],
            timeline_months=12,
            total_investment_usd=200000,
            expected_arr_contribution=300000,
        )

        return GlobalExpansionOutput(
            waves=[wave1],
            total_markets_assessed=2,
            recommended_first_market="United Kingdom",
            total_expansion_investment=200000,
            expected_global_arr=300000,
            expansion_timeline_months=12,
            key_risks=["Regulatory complexity", "Currency fluctuation", "Local competition"],
            recommendations=[
                "Start with English-speaking markets to minimize localization costs",
                "Hire local sales lead in first expansion market",
            ],
            evidence=evidence[:10],
            confidence=ConfidenceScore(score=40.0, evidence=evidence[:5]),
            explanation="Fallback expansion plan — requires more market data for comprehensive analysis.",
        )
