"""Decision Intelligence — structured decision extraction and tracking.

Replaces simple summaries with structured decision extraction.
Generates a Decision Log across all meetings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from backend.modules.memory.types import MemoryEntry, MemoryType
from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    SUPERSEDED = "superseded"
    DEFERRED = "deferred"


class Decision(BaseModel):
    """A structured decision extracted from meeting discussions."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    decision: str = Field(max_length=1000, description="What was decided")
    reason: str = Field(max_length=1000, description="Why this decision was made")
    supporting_evidence: list[str] = Field(default_factory=list, description="Evidence that supports this decision")
    participants: list[str] = Field(default_factory=list, description="Who was involved")
    confidence: float = Field(ge=0.0, le=1.0, description="How confident are we in this decision")
    alternatives_rejected: list[str] = Field(default_factory=list, description="Other options considered and rejected")
    impacted_modules: list[str] = Field(default_factory=list, description="Pipeline stages affected")
    follow_up_actions: list[str] = Field(default_factory=list, description="Next steps")
    status: DecisionStatus = Field(default=DecisionStatus.ACCEPTED)
    category: str = Field(default="general", description="Business area")
    source_meeting_id: str = Field(description="Which meeting")
    source_refs: list[str] = Field(default_factory=list, description="Transcript references")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    superseded_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionLog(BaseModel):
    """Complete decision log for a startup."""
    project_id: str
    decisions: list[Decision] = Field(default_factory=list)
    total_decisions: int = 0
    pending_actions: int = 0
    implemented: int = 0
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DecisionExtractionResult(BaseModel):
    """Result of extracting decisions from a meeting."""
    decisions: list[Decision]
    contradictions: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)
    summary: str = ""


DECISION_EXTRACTION_PROMPT = """You are a Decision Intelligence Analyst. Extract ALL decisions from this meeting transcript.

## Meeting Context
- Meeting: {title}
- Date: {date}
- Participants: {participants}

## Previous Decisions (for reference)
{previous_decisions}

## Transcript
{transcript}

## Extract EVERY decision as:

For EACH decision:
1. decision: what was decided (clear, specific statement)
2. reason: why this decision was made (the rationale)
3. supporting_evidence: specific data points, quotes, or facts cited
4. participants: who was involved in making this decision
5. confidence: 0.0-1.0 (how clear and final was this decision)
6. alternatives_rejected: what other options were considered and why rejected
7. impacted_modules: which pipeline stages this affects
8. follow_up_actions: what needs to happen next
9. category: pricing/features/hiring/roadmap/funding/marketing/technical/legal/strategy/operations

## Rules:
- Extract EVERY decision, even if it seems minor
- Capture the reasoning, not just the outcome
- Note what alternatives were considered
- Identify which pipeline stages need updating
- If a decision reverses a previous decision, note the previous decision ID

Return as JSON array of Decision objects."""

DECISION_CONSOLIDATION_PROMPT = """Consolidate decisions from multiple meetings into a coherent log.

## Decisions Log
{decisions}

## Find:
1. Decisions that contradict each other → keep the most recent
2. Decisions that were superseded → mark as superseded
3. Decisions that are still pending → keep active
4. Decisions that have been implemented → mark as implemented

Return consolidated list with updated statuses."""


class DecisionIntelligence:
    """Extracts, tracks, and manages startup decisions."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.log = DecisionLog(project_id=project_id)

    async def extract_decisions(
        self,
        meeting_id: str,
        title: str,
        date: str,
        participants: list[str],
        transcript: str,
    ) -> DecisionExtractionResult:
        """Extract decisions from a meeting transcript."""
        previous_decisions = self._format_previous_decisions()

        prompt = DECISION_EXTRACTION_PROMPT.format(
            title=title,
            date=date,
            participants=", ".join(participants),
            previous_decisions=previous_decisions,
            transcript=transcript[:8000],
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=list[dict[str, Any]],
                system_instruction="You extract structured decisions from meeting transcripts.",
            )

            decisions = []
            affected_modules: set[str] = set()
            contradictions: list[str] = []

            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        decision = Decision(
                            decision=item.get("decision", ""),
                            reason=item.get("reason", ""),
                            supporting_evidence=item.get("supporting_evidence", []),
                            participants=item.get("participants", []),
                            confidence=float(item.get("confidence", 0.8)),
                            alternatives_rejected=item.get("alternatives_rejected", []),
                            impacted_modules=item.get("impacted_modules", []),
                            follow_up_actions=item.get("follow_up_actions", []),
                            category=item.get("category", "general"),
                            source_meeting_id=meeting_id,
                            source_refs=item.get("source_refs", []),
                        )
                        decisions.append(decision)
                        for mod in decision.impacted_modules:
                            affected_modules.add(mod)

            # Add to log
            self.log.decisions.extend(decisions)
            self.log.total_decisions = len(self.log.decisions)
            self.log.pending_actions = sum(
                1 for d in self.log.decisions
                if d.follow_up_actions and d.status != DecisionStatus.IMPLEMENTED
            )
            self.log.last_updated = datetime.now(timezone.utc).isoformat()

            return DecisionExtractionResult(
                decisions=decisions,
                contradictions=contradictions,
                affected_modules=list(affected_modules),
                summary=f"Extracted {len(decisions)} decisions from '{title}'",
            )

        except Exception as e:
            logger.warning(f"Decision extraction failed: {e}")
            return DecisionExtractionResult(decisions=[], summary=f"Extraction failed: {str(e)[:100]}")

    def _format_previous_decisions(self) -> str:
        """Format previous decisions for context."""
        if not self.log.decisions:
            return "No previous decisions."

        recent = sorted(self.log.decisions, key=lambda d: d.created_at, reverse=True)[:10]
        parts = []
        for d in recent:
            parts.append(f"- [{d.status.value}] {d.decision[:80]} (confidence: {d.confidence:.0%})")
        return "\n".join(parts)

    def get_by_category(self, category: str) -> list[Decision]:
        """Get decisions by category."""
        return [d for d in self.log.decisions if d.category == category]

    def get_pending_actions(self) -> list[Decision]:
        """Get decisions with pending follow-up actions."""
        return [
            d for d in self.log.decisions
            if d.follow_up_actions and d.status not in (DecisionStatus.IMPLEMENTED, DecisionStatus.REJECTED)
        ]

    def get_recent(self, limit: int = 10) -> list[Decision]:
        """Get most recent decisions."""
        return sorted(self.log.decisions, key=lambda d: d.created_at, reverse=True)[:limit]

    def search(self, query: str) -> list[Decision]:
        """Search decisions by keyword."""
        q = query.lower()
        return [
            d for d in self.log.decisions
            if q in d.decision.lower() or q in d.reason.lower()
        ]

    def to_memory_entries(self) -> list[MemoryEntry]:
        """Convert decisions to memory entries for the memory engine."""
        entries = []
        for d in self.log.decisions:
            entries.append(MemoryEntry(
                memory_type=MemoryType.DECISION,
                content=f"{d.decision} — Reason: {d.reason}",
                category=d.category,
                confidence=d.confidence,
                source_meeting_id=d.source_meeting_id,
                source_transcript_refs=d.source_refs,
                affected_modules=d.impacted_modules,
            ))
        return entries
