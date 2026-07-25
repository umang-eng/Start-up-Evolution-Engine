"""Risk Analyst Agent — identifies, quantifies, and prioritizes business risks."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class RiskAnalystAgent(SpecializedAgent):
    role = "Risk Analyst"
    expertise = "Risk identification, quantification, mitigation planning, scenario analysis"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        product = context.get("product_description", "")
        features = context.get("features", [])

        risk_evidence = await search_evidence(
            f"{industry} startup risks challenges failure modes 2025", max_results=4
        )
        evidence.extend(risk_evidence)

        risk_level = self._assess_risk_level(context, evidence)
        mitigation = self._assess_mitigation_quality(context, evidence)
        overall = self._overall_risk_score(context, evidence)

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, risk_level, mitigation, overall),
            scores=[risk_level, mitigation, overall],
            key_findings=[
                f"Risk level: {risk_level.value:.0f}/100 (higher = less risky)",
                f"Mitigation quality: {mitigation.value:.0f}/100",
                f"Overall risk position: {overall.value:.0f}/100",
            ],
            risks_identified=self._all_risks(context, evidence),
            recommendations=self._recommendations(context, evidence),
            confidence=self._build_confidence(
                overall.confidence.score, evidence,
                missing=["Historical failure rate data for this specific vertical"],
                assumptions=["Risk patterns from similar startups are applicable"]
            ),
            disagreements=["May differ from optimists on severity of market risks"],
        )

    def _assess_risk_level(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        risk_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["risk", "fail", "challenge", "threat"])]
        # More risk signals = lower score (worse risk position)
        val = 75 - min(len(risk_signals) * 4, 30) if risk_signals else 60
        return EvidenceBackedScore(
            value=max(25, min(val, 90)),
            label="Risk Level",
            confidence=self._build_confidence(val, risk_signals),
            explanation=f"{len(risk_signals)} risk indicators found."
        )

    def _assess_mitigation_quality(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        mitigation_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["mitigat", "strateg", "plan", "backup"])]
        val = 55 + min(len(mitigation_signals) * 6, 25) if mitigation_signals else 48
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Mitigation Quality",
            confidence=self._build_confidence(val, mitigation_signals),
            explanation=f"{len(mitigation_signals)} mitigation signals found."
        )

    def _overall_risk_score(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        risk = self._assess_risk_level(ctx, evidence)
        mit = self._assess_mitigation_quality(ctx, evidence)
        val = (risk.value * 0.6 + mit.value * 0.4)
        return EvidenceBackedScore(
            value=val,
            label="Overall Risk Position",
            confidence=self._build_confidence(val, evidence[:5]),
            explanation=f"Composite of risk level ({risk.value:.0f}) and mitigation ({mit.value:.0f})."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        risk_val = scores[0].value
        risk_label = "LOW" if risk_val > 70 else "MODERATE" if risk_val > 50 else "HIGH"
        return (
            f"Risk assessment: Level {risk_val:.0f}/100 ({risk_label}), "
            f"Mitigation {scores[1].value:.0f}/100, Overall {scores[2].value:.0f}/100. "
            f"Based on {len(evidence)} evidence sources."
        )

    def _all_risks(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        risks = []
        for e in evidence:
            if "risk" in e.snippet.lower() or "threat" in e.snippet.lower():
                risks.append(f"{e.source_name}: {e.snippet[:80]}")
        if not risks:
            risks.append("No specific risks identified from evidence — conduct deeper analysis")
        return risks[:6]

    def _recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        return [
            "Develop detailed risk register with probability and impact for each identified risk",
            "Create contingency plans for top 3 risks before launch",
            "Establish early warning indicators for critical risk thresholds",
        ]
