"""Market Analyst Agent — assesses market size, growth, trends, and timing."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource
)
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class MarketAnalystAgent(SpecializedAgent):
    role = "Market Analyst"
    expertise = "Market sizing, growth trends, competitive landscape, timing"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        product = context.get("product_description", "")
        target_market = context.get("target_market", "")

        # Gather additional evidence if not enough
        if len(evidence) < 5:
            extra = await search_evidence(f"{industry} market size growth 2025 2026", max_results=5)
            evidence = evidence + extra

        # Search for specific market data
        market_data = await search_evidence(
            f"{industry} total addressable market TAM SAM SOM 2025", max_results=3
        )
        evidence.extend(market_data)

        # Build scores
        market_size_score = self._score_market_size(context, evidence)
        growth_score = self._score_growth_potential(context, evidence)
        timing_score = self._score_market_timing(context, evidence)
        competition_score = self._score_competitive_intensity(context, evidence)

        missing = []
        if not any("market size" in e.snippet.lower() for e in evidence):
            missing.append("Verified market size data from authoritative source")
        if not any("growth rate" in e.snippet.lower() or "cagr" in e.snippet.lower() for e in evidence):
            missing.append("Industry growth rate / CAGR data")
        if not any("competitor" in e.snippet.lower() for e in evidence):
            missing.append("Competitor landscape data")

        assumptions = [
            f"Industry '{industry}' is the correct categorization",
            f"Target market '{target_market}' represents the primary addressable segment",
            "Market data from web sources is reasonably current",
        ]

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, market_size_score, growth_score, timing_score),
            scores=[market_size_score, growth_score, timing_score, competition_score],
            key_findings=self._extract_findings(evidence, context),
            risks_identified=self._identify_risks(context, evidence),
            recommendations=self._make_recommendations(context, evidence),
            confidence=self._build_confidence(
                (market_size_score.confidence.score + growth_score.confidence.score) / 2,
                evidence, missing, assumptions
            ),
            disagreements=self._find_disagreements(evidence),
        )

    def _score_market_size(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        # Look for market size signals in evidence
        size_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["billion", "million", "market size", "tam"])]
        if len(size_signals) >= 3:
            val = 80 + min(len(size_signals) * 3, 15)
        elif len(size_signals) >= 1:
            val = 60 + min(len(size_signals) * 5, 15)
        else:
            val = 40

        return EvidenceBackedScore(
            value=min(val, 95),
            label="Market Size Opportunity",
            confidence=self._build_confidence(
                val, size_signals,
                missing=["Direct TAM/SAM/SOM figures"] if not size_signals else [],
                assumptions=["Market boundaries are well-defined"]
            ),
            explanation=f"Based on {len(size_signals)} market size data points found in evidence."
        )

    def _score_growth_potential(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        growth_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["growth", "cagr", "increasing", "expanding"])]
        if len(growth_signals) >= 3:
            val = 78 + min(len(growth_signals) * 3, 15)
        elif len(growth_signals) >= 1:
            val = 55 + min(len(growth_signals) * 5, 15)
        else:
            val = 45
        return EvidenceBackedScore(
            value=min(val, 95),
            label="Growth Potential",
            confidence=self._build_confidence(val, growth_signals),
            explanation=f"Based on {len(growth_signals)} growth indicators in evidence."
        )

    def _score_market_timing(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        timing_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["emerging", "early", "timing", "window", "trend"])]
        val = 60 + min(len(timing_signals) * 5, 25) if timing_signals else 50
        return EvidenceBackedScore(
            value=min(val, 90),
            label="Market Timing",
            confidence=self._build_confidence(val, timing_signals),
            explanation=f"Timing assessment based on {len(timing_signals)} signals."
        )

    def _score_competitive_intensity(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        comp_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["competitor", "rival", "market share", "alternative"])]
        # More competitors = lower score
        if len(comp_signals) >= 5:
            val = 40
        elif len(comp_signals) >= 3:
            val = 55
        else:
            val = 75
        return EvidenceBackedScore(
            value=val,
            label="Competitive Intensity",
            confidence=self._build_confidence(val, comp_signals),
            explanation=f"Found {len(comp_signals)} competitor signals. {'High' if val < 50 else 'Moderate' if val < 65 else 'Low'} intensity."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        industry = ctx.get("industry", "the industry")
        score_summary = ", ".join(f"{s.label}: {s.value:.0f}" for s in scores)
        return (
            f"Market analysis for {industry}: {score_summary}. "
            f"Based on {len(evidence)} evidence sources. "
            f"Market conditions appear {'favorable' if scores[0].value > 70 else 'moderate' if scores[0].value > 50 else 'challenging'}."
        )

    def _extract_findings(self, evidence: list[EvidenceSource], ctx: dict) -> list[str]:
        findings = []
        for e in evidence[:5]:
            if e.snippet:
                findings.append(f"{e.source_name}: {e.snippet[:100]}")
        if not findings:
            findings.append(f"Market research conducted for {ctx.get('industry', 'target industry')}")
        return findings[:5]

    def _identify_risks(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        risks = []
        if len(evidence) < 5:
            risks.append("Limited market evidence available — conclusions may be unreliable")
        comp_count = sum(1 for e in evidence if "competitor" in e.snippet.lower())
        if comp_count >= 4:
            risks.append("Highly competitive market — differentiation critical")
        if not any("regulation" in e.snippet.lower() for e in evidence):
            risks.append("Regulatory landscape unclear — potential compliance risks")
        return risks[:4]

    def _make_recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        recs = []
        if len(evidence) >= 5:
            recs.append("Sufficient market evidence found to proceed with analysis")
        recs.append("Validate market size assumptions with primary customer research")
        recs.append("Monitor competitor movements closely in early stages")
        return recs[:3]

    def _find_disagreements(self, evidence: list[EvidenceSource]) -> list[str]:
        disagreements = []
        positive = [e for e in evidence if any(w in e.snippet.lower() for w in ["growth", "increasing", "booming"])]
        negative = [e for e in evidence if any(w in e.snippet.lower() for w in ["declining", "slowdown", "challenge"])]
        if positive and negative:
            disagreements.append("Mixed signals: some evidence points to growth while other indicates headwinds")
        return disagreements
