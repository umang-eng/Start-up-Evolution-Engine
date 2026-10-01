"""Global Expansion Engine Module — multi-country expansion analysis with evidence.

Generates detailed expansion plans for multiple countries with regulatory,
hiring, pricing, and GTM analysis for each.
"""

from __future__ import annotations

from typing import Any

from backend.ai.ollama import ollama_adapter
from backend.modules.global_expansion.schemas import (
    GlobalExpansionOutput, CountryExpansion, ExpansionWave
)
from backend.modules.evidence.types import ConfidenceScore, EvidenceSource
from backend.modules.evidence.collector import search_evidence, gather_regulatory_evidence
from backend.core.config import settings


EXPANSION_PROMPT = """You are a Global Expansion Strategist planning international market entry.

## Startup Context
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Stage: {stage}
- Home Market: {home_market}
- Monthly Burn: ${monthly_burn:,.0f}
- Stated Available Capital (0 means not supplied): ${available_capital:,.0f}

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

Do not invent competitor names, market sizes, taxes, regulations, funding, or available capital.
Separate sourced facts from planning estimates and mark unknowns explicitly. Do not treat regulations
as mandatory unless the startup's activities, data, and target market satisfy their scope. If the home
market is unspecified, say so rather than assuming one.
Do not count the home market itself as an expansion destination.

Return valid GlobalExpansionOutput JSON."""


class GlobalExpansionModule:
    """Generates comprehensive global expansion analysis with evidence-backed assessments."""

    stage_name = "global_expansion"
    input_stages = ["dna", "features", "roadmap", "cost", "blueprint"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []
        industry = context.get("industry", "technology")

        # Gather global expansion evidence
        if not settings.PIPELINE_FAST_MODE:
            expansion_evidence = await search_evidence(
                f"{industry} international expansion global markets 2025", max_results=4
            )
            evidence.extend(expansion_evidence)

        # Gather regulatory evidence for key markets
        target_countries = ["United States", "United Kingdom", "Germany", "Japan", "India", "Brazil"]
        if not settings.PIPELINE_FAST_MODE:
            reg_evidence = await gather_regulatory_evidence(industry, target_countries)
            for country_evs in reg_evidence.values():
                evidence.extend(country_evs)

        # Fast mode skips optional evidence collection, not the expansion analysis itself.
        output = await self._generate_expansion(context, evidence)
        return output.model_dump()

    async def _generate_expansion(
        self, context: dict[str, Any], evidence: list[EvidenceSource]
    ) -> GlobalExpansionOutput:
        """Generate global expansion analysis."""
        if not evidence:
            return self._fallback_output([])

        cost = context.get("cost_output") or context.get("cost", {})
        monthly_burn = float(cost.get("monthly_burn_usd", 0) or cost.get("total_monthly_payroll_usd", 0) or 0)

        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:120]}"
            for e in evidence[:20]
        ) or "No evidence available"

        prompt = EXPANSION_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            stage=context.get("stage", "pre-seed"),
            home_market=context.get("home_market") or context.get("region") or "Not supplied",
            monthly_burn=monthly_burn,
            available_capital=float(context.get("available_capital_usd", 0) or 0),
            evidence_text=evidence_text,
        )

        result = await ollama_adapter.generate(
            prompt=prompt,
            schema=GlobalExpansionOutput,
            system_instruction="You are a Global Expansion Strategist planning international market entry.",
        )

        if isinstance(result, GlobalExpansionOutput):
            result.evidence = evidence[:15]
            return result

        return self._fallback_output(evidence)

    def _fallback_output(self, evidence: list[EvidenceSource]) -> GlobalExpansionOutput:
        """Return an explicit unknown baseline rather than inventing countries or costs."""
        wave1 = ExpansionWave(
            wave_number=1,
            wave_name="Not assessed",
            countries=[],
            timeline_months=0,
            total_investment_usd=0,
            expected_arr_contribution=0,
        )

        return GlobalExpansionOutput(
            waves=[wave1],
            total_markets_assessed=0,
            recommended_first_market="Undetermined",
            total_expansion_investment=0,
            expected_global_arr=0,
            expansion_timeline_months=0,
            key_risks=["Destination markets, regulatory scope, and expansion budget have not been validated."],
            recommendations=["Validate target-country demand and obtain country-specific legal, tax, hiring, and operating-cost advice before planning entry."],
            evidence=evidence[:10],
            confidence=ConfidenceScore(
                score=0.0,
                evidence=evidence[:5],
                missing_information=["Target countries", "Country-level market evidence", "Available expansion capital"],
            ),
            explanation="No expansion markets or financial estimates were assessed; figures are intentionally left unknown.",
        )
