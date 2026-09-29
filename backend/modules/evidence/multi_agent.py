"""Multi-Agent Decision System — specialized agents with a Judge for consensus.

Each agent produces an independent, evidence-backed assessment. The Judge
compares all opinions, resolves conflicts, explains disagreements, and
produces the final decision with overall confidence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field

from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, ExplainableDecision
)


class AgentOpinion(BaseModel):
    """Output from a single specialized agent."""
    agent_role: str = Field(description="Role of the agent (e.g., 'Market Analyst')")
    assessment: str = Field(max_length=2000, description="Agent's assessment")
    scores: list[EvidenceBackedScore] = Field(default_factory=list, description="Scores with confidence")
    key_findings: list[str] = Field(min_length=1, max_length=10, description="Top findings")
    risks_identified: list[str] = Field(default_factory=list, description="Risks this agent sees")
    recommendations: list[str] = Field(default_factory=list, description="Agent's recommendations")
    confidence: ConfidenceScore = Field(description="Overall confidence in this assessment")
    disagreements: list[str] = Field(
        default_factory=list,
        description="Areas where this agent disagrees with typical consensus"
    )


class JudgeVerdict(BaseModel):
    """Final verdict from the Judge after reviewing all agent opinions."""
    final_assessment: str = Field(max_length=3000, description="Synthesized final assessment")
    consensus_scores: list[EvidenceBackedScore] = Field(
        default_factory=list,
        description="Final scores after reconciling all opinions"
    )
    agreements: list[str] = Field(description="Areas where agents agreed")
    conflicts: list[str] = Field(description="Areas where agents disagreed")
    conflict_resolutions: list[str] = Field(description="How each conflict was resolved")
    overall_confidence: ConfidenceScore = Field(description="Overall confidence in the final verdict")
    dissenting_views: list[str] = Field(
        default_factory=list,
        description="Minority opinions that were overruled but worth tracking"
    )
    key_risks: list[str] = Field(default_factory=list, description="Consolidated key risks")
    recommendations: list[str] = Field(default_factory=list, description="Final recommendations")


class SpecializedAgent(ABC):
    """Base class for specialized agents in the decision system."""
    role: str
    expertise: str

    @abstractmethod
    async def assess(self, context: dict[str, Any], evidence: list[EvidenceSource]) -> AgentOpinion:
        """Produce an independent, evidence-backed assessment."""
        ...

    def _build_confidence(
        self, score: float, evidence: list[EvidenceSource],
        missing: list[str] | None = None, assumptions: list[str] | None = None
    ) -> ConfidenceScore:
        """Build a confidence score from available evidence."""
        base = min(score, 100.0)
        evidence_bonus = min(len(evidence) * 3, 20)
        missing_penalty = len(missing or []) * 5
        final = max(0.0, min(100.0, base + evidence_bonus - missing_penalty))
        return ConfidenceScore(
            score=final,
            evidence=evidence[:10],
            missing_information=missing or [],
            assumptions=assumptions or [],
        )


class Judge:
    """The Investment Committee Judge that synthesizes agent opinions."""
    role = "Investment Committee Judge"
    expertise = "Synthesis, conflict resolution, final decision-making"

    async def deliberate(self, opinions: list[AgentOpinion]) -> JudgeVerdict:
        """Compare all opinions, resolve conflicts, produce final verdict."""
        agreements: list[str] = []
        conflicts: list[str] = []
        resolutions: list[str] = []
        dissenting: list[str] = []
        all_risks: list[str] = []
        all_recommendations: list[str] = []

        # Find agreements: opinions that appear in 60%+ of agents
        threshold = max(1, int(len(opinions) * 0.6))
        opinion_texts = [op.assessment.lower() for op in opinions]
        key_findings_flat: list[str] = []
        for op in opinions:
            key_findings_flat.extend(op.key_findings)

        # Find conflicts: directly opposing views
        for i, op_i in enumerate(opinions):
            for j, op_j in enumerate(opinions):
                if i >= j:
                    continue
                for finding_i in op_i.disagreements:
                    for finding_j in op_j.key_findings:
                        if self._is_conflict(finding_i, finding_j):
                            conflict_desc = f"{op_i.agent_role} vs {op_j.agent_role}: {finding_i} vs {finding_j}"
                            conflicts.append(conflict_desc)
                            resolution = self._resolve_conflict(op_i, op_j, finding_i, finding_j)
                            resolutions.append(resolution)

        # Deduplicate agreements from overlapping findings
        seen_agreements: set[str] = set()
        for finding in key_findings_flat:
            normalized = finding.lower().strip()
            if normalized not in seen_agreements and self._appears_in_many(opinions, finding):
                agreements.append(finding)
                seen_agreements.add(normalized)

        # Collect dissenting views
        for op in opinions:
            for d in op.disagreements:
                dissenting.append(f"{op.agent_role}: {d}")

        # Consolidate risks and recommendations
        for op in opinions:
            for r in op.risks_identified:
                if r not in all_risks:
                    all_risks.append(r)
            for rec in op.recommendations:
                if rec not in all_recommendations:
                    all_recommendations.append(rec)

        # Build final assessment
        assessments = [f"**{op.agent_role}**: {op.assessment[:200]}" for op in opinions]
        final_assessment = (
            "## Judge's Synthesis\n\n"
            + "\n\n".join(assessments)
            + f"\n\n### Agreements ({len(agreements)}): " + "; ".join(agreements[:5])
            + f"\n\n### Conflicts ({len(conflicts)}): " + "; ".join(conflicts[:5])
            + f"\n\n### Resolutions: " + "; ".join(resolutions[:5])
        )

        # Compute overall confidence from agent confidences
        agent_confidences = [op.confidence.score for op in opinions]
        avg_confidence = sum(agent_confidences) / len(agent_confidences) if agent_confidences else 50.0
        agreement_bonus = min(len(agreements) * 2, 15)
        conflict_penalty = min(len(conflicts) * 3, 20)
        overall_confidence = max(10.0, min(100.0, avg_confidence + agreement_bonus - conflict_penalty))

        # Build consensus scores (average of agent scores for same metrics)
        consensus_scores = self._build_consensus_scores(opinions)

        return JudgeVerdict(
            final_assessment=final_assessment,
            consensus_scores=consensus_scores,
            agreements=agreements,
            conflicts=conflicts,
            conflict_resolutions=resolutions,
            overall_confidence=ConfidenceScore(
                score=overall_confidence,
                evidence=[],  # Populated by caller
                missing_information=[
                    f"Agent {op.agent_role} reported missing info: {', '.join(op.confidence.missing_information[:3])}"
                    for op in opinions if op.confidence.missing_information
                ],
            ),
            dissenting_views=dissenting,
            key_risks=all_risks[:10],
            recommendations=all_recommendations[:10],
        )

    def _is_conflict(self, text_a: str, text_b: str) -> bool:
        """Detect if two statements are in conflict."""
        opposing_pairs = [
            ("high", "low"), ("strong", "weak"), ("growing", "declining"),
            ("positive", "negative"), ("opportunity", "threat"),
            ("favorable", "unfavorable"), ("viable", "not viable"),
            ("invest", "avoid"), ("enter", "avoid entering"),
        ]
        a_lower = text_a.lower()
        b_lower = text_b.lower()
        for pos, neg in opposing_pairs:
            if (pos in a_lower and neg in b_lower) or (neg in a_lower and pos in b_lower):
                return True
        return False

    def _resolve_conflict(self, op_a: AgentOpinion, op_b: AgentOpinion,
                          finding_a: str, finding_b: str) -> str:
        """Resolve a conflict between two agents by weighing evidence."""
        conf_a = op_a.confidence.score
        conf_b = op_b.confidence.score
        if conf_a > conf_b + 10:
            return f"Relying on {op_a.agent_role} (confidence {conf_a:.0f}% vs {conf_b:.0f}%): {finding_a}"
        elif conf_b > conf_a + 10:
            return f"Relying on {op_b.agent_role} (confidence {conf_b:.0f}% vs {conf_a:.0f}%): {finding_b}"
        else:
            return f"Split decision between {op_a.agent_role} and {op_b.agent_role}; leaning toward middle ground"

    def _appears_in_many(self, opinions: list[AgentOpinion], finding: str) -> bool:
        """Check if a finding appears in 60%+ of agent opinions."""
        count = 0
        for op in opinions:
            for f in op.key_findings:
                if finding.lower()[:30] in f.lower() or f.lower()[:30] in finding.lower():
                    count += 1
                    break
        return count >= max(1, int(len(opinions) * 0.6))

    def _build_consensus_scores(self, opinions: list[AgentOpinion]) -> list[EvidenceBackedScore]:
        """Average agent scores for the same metric labels."""
        score_map: dict[str, list[EvidenceBackedScore]] = {}
        for op in opinions:
            for s in op.scores:
                if s.label not in score_map:
                    score_map[s.label] = []
                score_map[s.label].append(s)

        consensus: list[EvidenceBackedScore] = []
        for label, scores in score_map.items():
            avg_val = sum(s.value for s in scores) / len(scores)
            all_evidence: list[EvidenceSource] = []
            for s in scores:
                all_evidence.extend(s.confidence.evidence)
            avg_conf = sum(s.confidence.score for s in scores) / len(scores)
            consensus.append(EvidenceBackedScore(
                value=avg_val,
                label=label,
                confidence=ConfidenceScore(
                    score=avg_conf,
                    evidence=all_evidence[:10],
                    missing_information=[],  # Aggregated from agents
                ),
                explanation=f"Consensus from {len(scores)} agents: avg={avg_val:.1f}",
            ))
        return consensus
