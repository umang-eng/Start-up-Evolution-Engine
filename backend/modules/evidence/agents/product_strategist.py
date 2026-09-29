"""Product Strategist Agent — assesses product-market fit, feature viability, and differentiation."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class ProductStrategistAgent(SpecializedAgent):
    role = "Product Strategist"
    expertise = "Product-market fit, feature prioritization, user needs, differentiation"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        product = context.get("product_description", "")
        features = context.get("features", [])
        target = context.get("target_market", "")

        if len(evidence) < 5:
            extra = await search_evidence(f"{product} product features reviews users", max_results=5)
            evidence = evidence + extra

        user_signals = await search_evidence(f"{target} user needs pain points {industry}", max_results=3)
        evidence.extend(user_signals)

        pmf_score = self._score_pmf(context, evidence)
        diff_score = self._score_differentiation(context, evidence)
        feature_score = self._score_feature_viability(context, evidence)

        missing = []
        if not features:
            missing.append("Feature list from pipeline")
        if not any("user" in e.snippet.lower() for e in evidence):
            missing.append("Direct user feedback or demand signals")

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, pmf_score, diff_score, feature_score),
            scores=[pmf_score, diff_score, feature_score],
            key_findings=self._findings(evidence, context),
            risks_identified=self._risks(context, evidence),
            recommendations=self._recommendations(context, evidence),
            confidence=self._build_confidence(
                (pmf_score.confidence.score + diff_score.confidence.score) / 2,
                evidence, missing,
                [f"Product description interpreted from: {product[:80]}"]
            ),
        )

    def _score_pmf(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        user_evidence = [e for e in evidence if any(w in e.snippet.lower() for w in ["user", "customer", "demand", "need", "pain"])]
        val = 55 + min(len(user_evidence) * 6, 30) if user_evidence else 40
        return EvidenceBackedScore(
            value=min(val, 92),
            label="Product-Market Fit Signal",
            confidence=self._build_confidence(val, user_evidence),
            explanation=f"{len(user_evidence)} user/demand signals found."
        )

    def _score_differentiation(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        diff_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["unique", "different", "innovative", "first", "novel"])]
        val = 55 + min(len(diff_signals) * 7, 25) if diff_signals else 48
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Differentiation Strength",
            confidence=self._build_confidence(val, diff_signals),
            explanation=f"{len(diff_signals)} uniqueness signals found."
        )

    def _score_feature_viability(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        features = ctx.get("features", [])
        val = 70 if features else 50
        if len(features) > 20:
            val -= 10  # Too many features
        return EvidenceBackedScore(
            value=max(30, min(val, 90)),
            label="Feature Viability",
            confidence=self._build_confidence(val, evidence[:3]),
            explanation=f"Feature set of {len(features)} items assessed."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        product = ctx.get("product_description", "the product")[:80]
        return (
            f"Product strategy assessment for '{product}': "
            f"PMF signal {scores[0].value:.0f}/100, Differentiation {scores[1].value:.0f}/100, "
            f"Feature viability {scores[2].value:.0f}/100. "
            f"Based on {len(evidence)} evidence sources."
        )

    def _findings(self, evidence: list[EvidenceSource], ctx: dict) -> list[str]:
        findings = []
        for e in evidence[:4]:
            if e.snippet:
                findings.append(f"{e.source_name}: {e.snippet[:100]}")
        if not findings:
            findings.append(f"Product analysis conducted for {ctx.get('industry', 'target market')}")
        return findings[:5]

    def _risks(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        risks = []
        if not ctx.get("features"):
            risks.append("No feature specifications provided — product direction unclear")
        comp = [e for e in evidence if "competitor" in e.snippet.lower()]
        if len(comp) >= 3:
            risks.append("Strong existing competitors may make differentiation difficult")
        return risks[:3]

    def _recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        return [
            "Validate product assumptions with 10+ potential users before building",
            "Focus on 3-5 core differentiators rather than feature breadth",
        ]
