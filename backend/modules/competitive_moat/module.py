"""Competitive Moat Analysis Module — deep competitive moat assessment.

Replaces simple SWOT thinking with structured analysis of 10 moat types,
each backed by evidence, with difficulty/time/cost estimates.
"""

from __future__ import annotations

from typing import Any

from backend.ai.gemini import gemini_adapter
from backend.modules.competitive_moat.schemas import (
    CompetitiveMoatOutput, MoatDimension, MoatType
)
from backend.modules.evidence.types import EvidenceBackedScore, ConfidenceScore, EvidenceSource
from backend.modules.evidence.collector import search_evidence, gather_competitor_evidence
from backend.modules.evidence.pipeline import run_decision_pipeline


MOAT_ANALYSIS_PROMPT = """You are a Competitive Strategy Analyst specializing in moat analysis.

Analyze the competitive moat for this startup. Evaluate ALL 10 moat dimensions.

## Startup Context
- Industry: {industry}
- Product: {product_description}
- Target Market: {target_market}
- Key Features: {features_summary}

## Competitors
{competitors_text}

## Evidence Gathered
{evidence_text}

## Moat Dimensions to Evaluate

For EACH of these 10 moat types, assess:
1. **Network Effects**: Does the product become more valuable as more users join?
2. **Data Moat**: Does the startup accumulate proprietary data that improves the product?
3. **Brand Moat**: Is there brand recognition or trust that competitors lack?
4. **Technology Moat**: Is there proprietary technology that is hard to replicate?
5. **Switching Costs**: How costly is it for customers to switch to a competitor?
6. **Economies of Scale**: Does the startup gain cost advantages at scale?
7. **Regulatory Advantage**: Are there licenses, patents, or regulations that protect the startup?
8. **Distribution Advantage**: Does the startup have unique access to customers?
9. **Community Advantage**: Is there a community or network that creates lock-in?
10. **AI/Data Flywheel**: Does AI usage create a self-reinforcing improvement loop?

## Scoring Guidelines
- 0-2: No meaningful moat in this dimension
- 3-4: Weak moat, easily replicated
- 5-6: Moderate moat, some defensibility
- 7-8: Strong moat, difficult to replicate
- 9-10: Fortress moat, nearly impossible to replicate

For each moat type provide:
- strength (0-10)
- difficulty_to_copy: TRIVIAL/EASY/MODERATE/HARD/NEAR_IMPOSSIBLE
- time_to_copy_months: estimated months for well-funded competitor
- cost_to_copy_usd: estimated cost in USD
- explanation: why this score

Return a valid CompetitiveMoatOutput JSON."""

MOAT_BUILD_PROMPT = """Based on the moat analysis, provide specific recommendations for building missing moats.

Industry: {industry}
Product: {product_description}
Weakest Moats: {weakest_moats}
Current Features: {features_summary}

For each weak moat, recommend:
1. Specific actions to build this moat
2. Timeline and resource requirements
3. Expected moat strength after investment

Return as JSON with key "recommendations" as a list of strings."""


class CompetitiveMoatModule:
    """Analyzes competitive moats with evidence-backed scoring."""

    stage_name = "competitive_moat"
    input_stages = ["dna", "features", "roadmap", "team", "swot", "cost", "blueprint"]

    async def run(self, context: dict[str, Any], evidence: list[EvidenceSource] | None = None) -> dict[str, Any]:
        evidence = evidence or []
        dna = context.get("dna_output", {})
        features = context.get("features_output", {})
        competitors = dna.get("competitor_landscape", [])

        # Gather competitor evidence
        comp_names = [c.get("name", "") for c in competitors if isinstance(c, dict)][:5]
        if comp_names:
            comp_evidence = await gather_competitor_evidence(comp_names)
            for comp_ev_list in comp_evidence.values():
                evidence.extend(comp_ev_list)

        # Gather moat-specific evidence
        moat_evidence = await search_evidence(
            f"{context.get('industry', 'technology')} competitive moat barriers entry defensibility",
            max_results=5
        )
        evidence.extend(moat_evidence)

        # Run multi-agent decision pipeline for moat assessment
        decision_context = {
            **context,
            "stage": "competitive_moat",
        }
        decision_result = await run_decision_pipeline(decision_context, evidence)

        # Build moat dimensions from evidence and agent opinions
        moat_dimensions = await self._assess_moat_dimensions(context, evidence, decision_result)

        # Generate overall moat output
        output = await self._generate_moat_output(context, moat_dimensions, evidence)

        return output.model_dump()

    async def _assess_moat_dimensions(
        self, context: dict[str, Any], evidence: list[EvidenceSource],
        decision_result: dict[str, Any]
    ) -> list[MoatDimension]:
        """Assess each moat dimension using evidence and LLM analysis."""
        features = context.get("features_output", {})
        feature_list = features.get("features", [])
        features_summary = "\n".join(
            f"- {f.get('name', 'Feature')}: {f.get('description', '')[:80]}"
            for f in feature_list[:10] if isinstance(f, dict)
        )

        # Build evidence text for prompt
        evidence_text = "\n".join(
            f"- [{e.source_name}] {e.snippet[:150]}"
            for e in evidence[:20]
        )

        competitors = context.get("dna_output", {}).get("competitor_landscape", [])
        competitors_text = "\n".join(
            f"- {c.get('name', 'Unknown')}: {c.get('description', '')[:80]}"
            for c in competitors[:5] if isinstance(c, dict)
        )

        prompt = MOAT_ANALYSIS_PROMPT.format(
            industry=context.get("industry", "technology"),
            product_description=context.get("product_description", ""),
            target_market=context.get("target_market", ""),
            features_summary=features_summary,
            competitors_text=competitors_text,
            evidence_text=evidence_text,
        )

        result = await gemini_adapter.generate(
            prompt=prompt,
            schema=CompetitiveMoatOutput,
            system_instruction="You are a Competitive Strategy Analyst. Analyze competitive moats with evidence-backed scoring.",
        )

        if isinstance(result, CompetitiveMoatOutput):
            return result.moat_dimensions
        # Fallback: create dimensions from evidence
        return self._fallback_dimensions(evidence)

    def _fallback_dimensions(self, evidence: list[EvidenceSource]) -> list[MoatDimension]:
        """Create fallback moat dimensions when LLM fails."""
        return [
            MoatDimension(
                moat_type=MoatType.NETWORK_EFFECTS,
                strength=3.0,
                difficulty_to_copy="EASY",
                time_to_copy_months=6,
                cost_to_copy_usd=500000,
                explanation="Fallback assessment — insufficient evidence",
            )
        ]

    async def _generate_moat_output(
        self, context: dict[str, Any], dimensions: list[MoatDimension],
        evidence: list[EvidenceSource]
    ) -> CompetitiveMoatOutput:
        """Generate the final competitive moat output."""
        # Compute overall score as weighted average
        active_dims = [d for d in dimensions if d.is_active]
        all_dims = dimensions if dimensions else []

        if all_dims:
            avg_strength = sum(d.strength for d in all_dims) / len(all_dims)
            strongest = max(all_dims, key=lambda d: d.strength)
            weakest = min(all_dims, key=lambda d: d.strength)
        else:
            avg_strength = 3.0
            strongest = MoatDimension(
                moat_type=MoatType.TECHNOLOGY_MOAT, strength=3.0,
                difficulty_to_copy="EASY", time_to_copy_months=6,
                cost_to_copy_usd=500000, explanation="Default"
            )
            weakest = strongest

        # Find gaps
        gaps = [d for d in dimensions if d.strength < 4.0]
        strong = [d for d in dimensions if d.strength >= 7.0]

        overall_confidence = min(100.0, 50.0 + len(evidence) * 3)

        return CompetitiveMoatOutput(
            overall_moat_score=EvidenceBackedScore(
                value=avg_strength * 10,  # Scale 0-10 to 0-100
                label="Overall Moat Strength",
                confidence=ConfidenceScore(
                    score=overall_confidence,
                    evidence=evidence[:10],
                    missing_information=["Proprietary data access", "Patent filings"],
                    assumptions=["Evidence reflects current market state"],
                ),
                explanation=f"Average moat strength: {avg_strength:.1f}/10 across {len(dimensions)} dimensions.",
            ),
            moat_dimensions=dimensions,
            strongest_moat=strongest.moat_type.value,
            weakest_moat=weakest.moat_type.value,
            moat_gap_analysis=[
                f"{d.moat_type.value}: strength {d.strength}/10 — needs significant investment"
                for d in gaps
            ],
            build_recommendations=[
                f"Focus on building {d.moat_type.value} moat (currently {d.strength}/10)"
                for d in gaps[:3]
            ],
            competitive_position=(
                f"Strong competitive position with {len(strong)} strong moats" if strong else
                f"Limited competitive moats — {len(gaps)} dimensions need improvement"
            ),
            time_to_defensible=f"{max(d.time_to_copy_months for d in dimensions)} months" if dimensions else "Unknown",
            evidence=evidence[:15],
            assumptions=["Competitor intelligence is current", "Market dynamics are stable"],
            explanation=(
                f"Competitive moat analysis across {len(dimensions)} dimensions. "
                f"Strongest: {strongest.moat_type.value} ({strongest.strength}/10). "
                f"Weakest: {weakest.moat_type.value} ({weakest.strength}/10). "
                f"{len(gaps)} moats below threshold (4/10)."
            ),
        )
