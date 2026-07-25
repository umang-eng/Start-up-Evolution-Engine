"""Competitive Moat Analysis — replaces simple SWOT with deep moat assessment."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, MoatAssessment
)


class MoatType(str, Enum):
    NETWORK_EFFECTS = "network_effects"
    DATA_MOAT = "data_moat"
    BRAND_MOAT = "brand_moat"
    TECHNOLOGY_MOAT = "technology_moat"
    SWITCHING_COSTS = "switching_costs"
    ECONOMIES_OF_SCALE = "economies_of_scale"
    REGULATORY_ADVANTAGE = "regulatory_advantage"
    DISTRIBUTION_ADVANTAGE = "distribution_advantage"
    COMMUNITY_ADVANTAGE = "community_advantage"
    AI_DATA_FLYWHEEL = "ai_data_flywheel"


class MoatDimension(BaseModel):
    """Assessment of a single moat dimension."""
    moat_type: MoatType
    strength: float = Field(ge=0.0, le=10.0, description="0=none, 10=fortress")
    difficulty_to_copy: Literal["TRIVIAL", "EASY", "MODERATE", "HARD", "NEAR_IMPOSSIBLE"]
    time_to_copy_months: int = Field(ge=0, description="Months for well-funded competitor")
    cost_to_copy_usd: float = Field(ge=0.0, description="USD to replicate")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    explanation: str = Field(max_length=500)
    is_active: bool = Field(default=False, description="Whether startup currently has this moat")


class CompetitiveMoatOutput(BaseModel):
    """Full competitive moat analysis output."""
    overall_moat_score: EvidenceBackedScore = Field(description="Aggregate moat strength")
    moat_dimensions: list[MoatDimension] = Field(min_length=1, description="Assessment of each moat type")
    strongest_moat: str = Field(description="The strongest moat type")
    weakest_moat: str = Field(description="The weakest moat type")
    moat_gap_analysis: list[str] = Field(description="Critical moat gaps to address")
    build_recommendations: list[str] = Field(description="How to build missing moats")
    competitive_position: str = Field(description="Overall competitive position assessment")
    time_to_defensible: str = Field(description="Estimated time to build defensible moat")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    explanation: str = Field(max_length=2000, description="Full explanation with evidence citations")

    @field_validator("strongest_moat", "weakest_moat")
    @classmethod
    def validate_moat_name(cls, v: str) -> str:
        return v.strip()
