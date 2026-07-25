"""Investment Committee Judge Agent — final decision maker after reviewing all agent opinions."""

from __future__ import annotations

from typing import Any

from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore, EvidenceSource
from backend.modules.evidence.multi_agent import AgentOpinion, SpecializedAgent
from backend.modules.evidence.collector import search_evidence


class InvestmentCommitteeJudgeAgent(SpecializedAgent):
    role = "Investment Committee Judge"
    expertise = "Synthesis, conflict resolution, investment decision-making, final verdict"

    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        """The Judge doesn't produce an independent opinion — it synthesizes."""
        # This is called when Judge operates as a standalone agent
        # In normal flow, Judge.deliberate() is used instead
        return AgentOpinion(
            agent_role=self.role,
            assessment="Investment Committee Judge synthesizes all agent opinions into a final verdict.",
            scores=[],
            key_findings=["Judge synthesizes, not independently assesses"],
            risks_identified=[],
            recommendations=[],
            confidence=ConfidenceScore(score=50.0, evidence=evidence[:5]),
        )
