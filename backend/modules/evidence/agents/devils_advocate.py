"""Devil's Advocate Agent — challenges assumptions, finds weaknesses, argues against the startup."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class DevilsAdvocateAgent(SpecializedAgent):
    role = "Devil's Advocate"
    expertise = "Challenging assumptions, finding weaknesses, contrarian analysis"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        product = context.get("product_description", "")
        features = context.get("features", [])

        contrarian = await search_evidence(
            f"{industry} startup failure reasons why {product[:30]} might not work", max_results=4
        )
        evidence.extend(contrarian)

        assumption_score = self._challenge_assumptions(context, evidence)
        weakness_score = self._find_weaknesses(context, evidence)
        contrarian_score = self._contrarian_assessment(context, evidence)

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, assumption_score, weakness_score, contrarian_score),
            scores=[assumption_score, weakness_score, contrarian_score],
            key_findings=self._key_findings(context, evidence),
            risks_identified=self._attack_plans(context, evidence),
            recommendations=self._recommendations(context, evidence),
            confidence=self._build_confidence(
                (assumption_score.confidence.score + weakness_score.confidence.score) / 2,
                evidence,
                missing=["Actual customer interviews", "Real financial data from competitors"],
                assumptions=["Worst-case scenarios are worth examining"]
            ),
            disagreements=self._contrarian_points(context, evidence),
        )

    def _challenge_assumptions(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        # Score how many assumptions are challenged (higher = more assumptions challenged = worse for startup)
        assumptions = ctx.get("assumptions", [])
        features = ctx.get("features", [])
        challenge_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["fail", "challenge", "problem", "issue"])]
        # This score represents "how many assumptions are questionable" — higher is worse
        val = 40 + min(len(challenge_signals) * 4, 35) if challenge_signals else 35
        return EvidenceBackedScore(
            value=min(val, 85),
            label="Assumption Challenge Score",
            confidence=self._build_confidence(val, challenge_signals),
            explanation=f"{len(challenge_signals)} challenge signals found against core assumptions."
        )

    def _find_weaknesses(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        weakness_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["weakness", "gap", "missing", "lack"])]
        val = 40 + min(len(weakness_signals) * 5, 30) if weakness_signals else 35
        return EvidenceBackedScore(
            value=min(val, 80),
            label="Weakness Exposure",
            confidence=self._build_confidence(val, weakness_signals),
            explanation=f"{len(weakness_signals)} weakness indicators found."
        )

    def _contrarian_assessment(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        contrarian = [e for e in evidence if any(w in e.snippet.lower() for w in ["unlikely", "overestimated", "myth", "hype"])]
        val = 35 + min(len(contrarian) * 6, 30) if contrarian else 30
        return EvidenceBackedScore(
            value=min(val, 75),
            label="Contrarian Case Strength",
            confidence=self._build_confidence(val, contrarian),
            explanation=f"{len(contrarian)} contrarian signals found."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        return (
            f"Devil's Advocate analysis: Assumption challenges {scores[0].value:.0f}/100, "
            f"Weaknesses exposed {scores[1].value:.0f}/100, Contrarian case {scores[2].value:.0f}/100. "
            f"Based on {len(evidence)} evidence sources. "
            f"These scores indicate areas where the startup thesis is most vulnerable."
        )

    def _key_findings(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        findings = []
        for e in evidence[:4]:
            if e.snippet and any(w in e.snippet.lower() for w in ["fail", "risk", "challenge", "problem"]):
                findings.append(f"{e.source_name}: {e.snippet[:100]}")
        if not findings:
            findings.append("Limited contrarian evidence found — this could mean the thesis is strong or research is insufficient")
        return findings[:5]

    def _attack_plans(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        attacks = []
        if not ctx.get("features"):
            attacks.append("No clear product differentiation identified")
        attacks.append("Market timing assumptions may be optimistic")
        comp = [e for e in evidence if "competitor" in e.snippet.lower()]
        if len(comp) >= 3:
            attacks.append("Established competitors with more resources may outmaneuver")
        return attacks[:4]

    def _recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        return [
            "Interview 10 potential customers to validate demand assumptions",
            "Analyze 3 competitor failures in this space to avoid their mistakes",
            "Build MVP before committing to full feature set",
        ]

    def _contrarian_points(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        points = []
        for e in evidence:
            if any(w in e.snippet.lower() for w in ["unlikely", "overestimated", "myth"]):
                points.append(f"{e.source_name}: {e.snippet[:80]}")
        if not points:
            points.append("The contrarian case is not strongly supported by available evidence — more research needed")
        return points[:3]
