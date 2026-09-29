"""Technical Architect Agent — assesses technical feasibility, architecture, and scalability."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class TechnicalArchitectAgent(SpecializedAgent):
    role = "Technical Architect"
    expertise = "System architecture, scalability, technical risk, build vs buy"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        features = context.get("features", [])
        product = context.get("product_description", "")
        stage = context.get("stage", "pre-seed")

        tech_evidence = await search_evidence(
            f"{industry} technology stack architecture best practices 2025", max_results=4
        )
        evidence.extend(tech_evidence)

        feasibility = self._score_feasibility(context, evidence)
        scalability = self._score_scalability(context, evidence)
        tech_risk = self._score_tech_risk(context, evidence)

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, feasibility, scalability, tech_risk),
            scores=[feasibility, scalability, tech_risk],
            key_findings=[
                f"Technical feasibility: {feasibility.value:.0f}/100",
                f"Scalability readiness: {scalability.value:.0f}/100",
                f"Technology risk level: {tech_risk.value:.0f}/100",
            ],
            risks_identified=self._risks(context, evidence),
            recommendations=self._recommendations(context, evidence),
            confidence=self._build_confidence(
                (feasibility.confidence.score + scalability.confidence.score) / 2,
                evidence,
                missing=["Architecture diagrams", "Performance benchmarks"] if not features else [],
                assumptions=["Standard cloud infrastructure available"]
            ),
        )

    def _score_feasibility(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        features = ctx.get("features", [])
        complex_features = [f for f in features if isinstance(f, dict) and f.get("effort_estimate") in ("XL", "L")]
        val = 85 - len(complex_features) * 5 if complex_features else 75
        return EvidenceBackedScore(
            value=max(40, min(val, 95)),
            label="Technical Feasibility",
            confidence=self._build_confidence(val, evidence[:3]),
            explanation=f"{len(features)} features assessed, {len(complex_features)} high-effort."
        )

    def _score_scalability(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        scale_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["scalable", "cloud", "microservice", "distributed"])]
        val = 60 + min(len(scale_signals) * 5, 20) if scale_signals else 55
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Scalability Readiness",
            confidence=self._build_confidence(val, scale_signals),
            explanation=f"{len(scale_signals)} scalability indicators found."
        )

    def _score_tech_risk(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        risk_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["risk", "challenge", "complex", "unproven"])]
        val = 70 - min(len(risk_signals) * 5, 25) if risk_signals else 65
        return EvidenceBackedScore(
            value=max(30, min(val, 90)),
            label="Technology Risk",
            confidence=self._build_confidence(val, risk_signals),
            explanation=f"{len(risk_signals)} risk indicators found. Higher is better (lower risk)."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        return (
            f"Technical assessment: Feasibility {scores[0].value:.0f}/100, "
            f"Scalability {scores[1].value:.0f}/100, Tech Risk {scores[2].value:.0f}/100. "
            f"Based on {len(evidence)} evidence sources."
        )

    def _risks(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        risks = []
        features = ctx.get("features", [])
        if len(features) > 15:
            risks.append("Large feature set may cause scope creep and delivery delays")
        if not any("architect" in e.snippet.lower() or "architecture" in e.snippet.lower() for e in evidence):
            risks.append("No architecture review conducted — design decisions unvalidated")
        return risks[:3]

    def _recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        return [
            "Design for horizontal scalability from day one",
            "Use proven technology stack over cutting-edge for core infrastructure",
            "Build API-first architecture to enable future integrations",
        ]
