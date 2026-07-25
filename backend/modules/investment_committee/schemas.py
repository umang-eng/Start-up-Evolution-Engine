"""Investment Committee Simulation — realistic VC review with full decision documentation."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, InvestorRecommendation
)


class CommitteeMember(BaseModel):
    """A single Investment Committee member's assessment."""
    name: str = Field(description="VC partner name (generated)")
    firm: str = Field(description="VC firm name (generated)")
    thesis: str = Field(max_length=500, description="Their investment thesis")
    vote: Literal["INVEST", "PASS", "CONDITIONAL"]
    confidence: float = Field(ge=0.0, le=100.0)
    key_concern: str = Field(max_length=300, description="Their biggest concern")
    key_excitement: str = Field(max_length=300, description="What excites them most")
    suggested_terms: str = Field(max_length=200, description="Suggested deal terms")


class InvestmentCommitteeOutput(BaseModel):
    """Full Investment Committee simulation output."""
    recommendation: InvestorRecommendation = Field(description="Final recommendation")
    committee_members: list[CommitteeMember] = Field(min_length=1, max_length=7, description="Individual member assessments")
    vote_tally: dict[str, int] = Field(description="Vote count: INVEST/PASS/CONDITIONAL")
    deliberation_notes: list[str] = Field(description="Key discussion points")
    term_sheet: dict[str, Any] = Field(description="Proposed term sheet")
    due_diligence_status: dict[str, str] = Field(description="DD item status")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(description="Overall committee confidence")
    explanation: str = Field(max_length=2000)
