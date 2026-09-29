"""Conflict Detection — identifies disagreements and generates resolutions.

Detects opposing viewpoints, supporting arguments, evidence,
missing information, and unresolved conflicts.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

from backend.ai.gemini import gemini_adapter
from backend.core.logging import logger


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectedConflict(BaseModel):
    """A detected disagreement in meeting discussions."""
    id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    topic: str = Field(description="What is being disagreed about")
    party_a: str = Field(description="First viewpoint holder")
    party_a_view: str = Field(description="Party A's position")
    party_b: str = Field(description="Second viewpoint holder")
    party_b_view: str = Field(description="Party B's position")
    supporting_evidence_a: list[str] = Field(default_factory=list)
    supporting_evidence_b: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    severity: ConflictSeverity
    resolution_status: Literal["unresolved", "partially_resolved", "resolved"]
    recommended_compromise: str = Field(default="")
    business_impact: str = Field(default="", description="Impact if unresolved")
    source_meeting_id: str = ""
    source_refs: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConflictDetectionResult(BaseModel):
    """Result of conflict detection analysis."""
    conflicts: list[DetectedConflict]
    total_conflicts: int
    unresolved_count: int
    high_severity_count: int
    summary: str
    recommendations: list[str]


CONFLICT_DETECTION_PROMPT = """You are a Conflict Resolution Analyst. Detect disagreements in this meeting transcript.

## Meeting
- Title: {title}
- Participants: {participants}

## Transcript
{transcript}

## Detect ALL conflicts:

For EACH disagreement found:
1. topic: what is being disagreed about
2. party_a / party_b: who holds each viewpoint
3. party_a_view / party_b_view: their specific positions
4. supporting_evidence_a / supporting_evidence_b: evidence cited
5. missing_information: what info would help resolve
6. severity: low/medium/high/critical
7. resolution_status: unresolved/partially_resolved/resolved
8. recommended_compromise: suggested resolution
9. business_impact: what happens if unresolved

## Types of conflicts to detect:
- Strategic disagreements (direction, market, timing)
- Technical disagreements (architecture, approach)
- Resource allocation conflicts
- Priority conflicts
- Budget/financial disagreements
- Hiring/staffing disagreements
- Timeline/schedule conflicts
- Risk tolerance differences

Return valid ConflictDetectionResult JSON."""


class ConflictDetectionEngine:
    """Detects and analyzes conflicts in meeting discussions."""

    def __init__(self):
        self.all_conflicts: list[DetectedConflict] = []

    async def detect(
        self,
        meeting_id: str,
        title: str,
        participants: list[str],
        transcript: str,
    ) -> ConflictDetectionResult:
        """Detect conflicts in a meeting transcript."""
        prompt = CONFLICT_DETECTION_PROMPT.format(
            title=title,
            participants=", ".join(participants),
            transcript=transcript[:6000],
        )

        try:
            result = await gemini_adapter.generate(
                prompt=prompt,
                schema=ConflictDetectionResult,
                system_instruction="You detect disagreements and conflicts in meeting discussions.",
            )

            if isinstance(result, ConflictDetectionResult):
                result.source_meeting_id = meeting_id if hasattr(result, 'source_meeting_id') else meeting_id
                for conflict in result.conflicts:
                    conflict.source_meeting_id = meeting_id
                self.all_conflicts.extend(result.conflicts)
                return result

        except Exception as e:
            logger.warning(f"Conflict detection failed: {e}")

        return ConflictDetectionResult(
            conflicts=[],
            total_conflicts=0,
            unresolved_count=0,
            high_severity_count=0,
            summary="Conflict detection unavailable",
            recommendations=[],
        )

    def get_unresolved(self) -> list[DetectedConflict]:
        """Get all unresolved conflicts."""
        return [c for c in self.all_conflicts if c.resolution_status == "unresolved"]

    def get_by_severity(self, severity: ConflictSeverity) -> list[DetectedConflict]:
        """Get conflicts by severity."""
        return [c for c in self.all_conflicts if c.severity == severity]

    def get_trend(self, limit: int = 10) -> dict[str, Any]:
        """Analyze conflict trends."""
        recent = self.all_conflicts[-limit:]
        if not recent:
            return {"trend": "no_data", "total": 0}

        unresolved = sum(1 for c in recent if c.resolution_status == "unresolved")
        high = sum(1 for c in recent if c.severity in (ConflictSeverity.HIGH, ConflictSeverity.CRITICAL))

        return {
            "total": len(recent),
            "unresolved": unresolved,
            "high_severity": high,
            "resolution_rate": 1 - (unresolved / len(recent)) if recent else 0,
        }
