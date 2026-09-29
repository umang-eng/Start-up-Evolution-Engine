"""GTM Strategist Agent — assesses go-to-market strategy, channels, and launch plan."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class GTMStrategistAgent(SpecializedAgent):
    role = "GTM Strategist"
    expertise = "Go-to-market strategy, customer acquisition, channels, launch timing"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        industry = context.get("industry", "technology")
        product = context.get("product_description", "")
        target = context.get("target_market", "")

        gtm_evidence = await search_evidence(
            f"{industry} go-to-market strategy channels customer acquisition 2025", max_results=4
        )
        evidence.extend(gtm_evidence)

        channel_score = self._score_channel_strategy(context, evidence)
        acquisition = self._score_acquisition_viability(context, evidence)
        launch = self._score_launch_readiness(context, evidence)

        return AgentOpinion(
            agent_role=self.role,
            assessment=self._build_assessment(context, evidence, channel_score, acquisition, launch),
            scores=[channel_score, acquisition, launch],
            key_findings=[
                f"Channel strategy: {channel_score.value:.0f}/100",
                f"Customer acquisition viability: {acquisition.value:.0f}/100",
                f"Launch readiness: {launch.value:.0f}/100",
            ],
            risks_identified=self._risks(context, evidence),
            recommendations=self._recommendations(context, evidence),
            confidence=self._build_confidence(
                (channel_score.confidence.score + acquisition.confidence.score) / 2,
                evidence,
                missing=["Customer acquisition cost data", "Channel performance benchmarks"],
                assumptions=["Standard digital marketing channels available"]
            ),
        )

    def _score_channel_strategy(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        channel_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["channel", "marketing", "distribution", "acquisition"])]
        val = 58 + min(len(channel_signals) * 5, 22) if channel_signals else 50
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Channel Strategy",
            confidence=self._build_confidence(val, channel_signals),
            explanation=f"{len(channel_signals)} channel-related signals found."
        )

    def _score_acquisition_viability(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        acq_signals = [e for e in evidence if any(w in e.snippet.lower() for w in ["cac", "acquisition cost", "conversion", "retention"])]
        val = 55 + min(len(acq_signals) * 6, 22) if acq_signals else 48
        return EvidenceBackedScore(
            value=min(val, 88),
            label="Customer Acquisition Viability",
            confidence=self._build_confidence(val, acq_signals),
            explanation=f"{len(acq_signals)} acquisition signals found."
        )

    def _score_launch_readiness(self, ctx: dict, evidence: list[EvidenceSource]) -> EvidenceBackedScore:
        features = ctx.get("features", [])
        val = 60 + min(len(features) * 2, 20) if features else 45
        return EvidenceBackedScore(
            value=min(val, 85),
            label="Launch Readiness",
            confidence=self._build_confidence(val, evidence[:2]),
            explanation=f"Feature count: {len(features)}. Launch readiness assessed."
        )

    def _build_assessment(self, ctx: dict, evidence: list[EvidenceSource], *scores: EvidenceBackedScore) -> str:
        return (
            f"GTM analysis: Channel {scores[0].value:.0f}/100, "
            f"Acquisition {scores[1].value:.0f}/100, Launch {scores[2].value:.0f}/100. "
            f"Based on {len(evidence)} evidence sources."
        )

    def _risks(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        risks = []
        if not ctx.get("target_market"):
            risks.append("Target market not clearly defined — GTM efforts may be unfocused")
        comp = [e for e in evidence if "competitor" in e.snippet.lower()]
        if len(comp) >= 4:
            risks.append("Saturated market may drive up customer acquisition costs")
        return risks[:3]

    def _recommendations(self, ctx: dict, evidence: list[EvidenceSource]) -> list[str]:
        return [
            "Start with one primary acquisition channel before diversifying",
            "Build content marketing engine for organic growth alongside paid channels",
            "Target CAC payback period under 12 months",
        ]
