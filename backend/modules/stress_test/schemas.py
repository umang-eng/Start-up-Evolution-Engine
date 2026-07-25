"""Market Stress Testing — simulates future scenarios and their business impact."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, ScenarioAnalysis
)


class StressTestScenario(BaseModel):
    """A specific stress test scenario with full assessment."""
    scenario_id: str = Field(description="Unique identifier for this scenario")
    scenario_name: str = Field(description="Name of the scenario")
    category: Literal["COMPETITIVE", "MARKET", "REGULATORY", "TECHNOLOGICAL", "ECONOMIC", "OPERATIONAL"]
    description: str = Field(max_length=500)
    trigger_event: str = Field(max_length=300, description="What triggers this scenario")
    impact: Literal["CATASTROPHIC", "SEVERE", "MODERATE", "MINOR", "NEGLIGIBLE"]
    impact_score: float = Field(ge=0.0, le=10.0)
    probability: float = Field(ge=0.0, le=1.0)
    time_to_manifest_months: int = Field(ge=0, description="How long until impact is felt")
    duration_months: int = Field(ge=0, description="How long the impact lasts")
    affected_areas: list[str] = Field(description="Which business areas are affected")
    mitigation_strategy: str = Field(max_length=500)
    recovery_plan: str = Field(max_length=500)
    recovery_time_months: int = Field(ge=0, description="Months to recover")
    expected_outcome: str = Field(max_length=300)
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(default_factory=lambda: ConfidenceScore(score=50.0), description="Confidence in this assessment")
    early_warning_signs: list[str] = Field(default_factory=list, description="Signs this scenario is emerging")
    pre_positioning: list[str] = Field(default_factory=list, description="Actions to take now to prepare")


class StressTestOutput(BaseModel):
    """Complete stress test analysis output."""
    scenarios: list[StressTestScenario] = Field(min_length=1, description="All tested scenarios")
    overall_resilience: EvidenceBackedScore = Field(description="Overall business resilience score")
    worst_case_scenario: str = Field(description="The most damaging scenario name")
    most_likely_scenario: str = Field(description="The most likely negative scenario")
    risk_score: EvidenceBackedScore = Field(description="Aggregate risk score")
    resilience_recommendations: list[str] = Field(description="How to improve resilience")
    early_warning_system: list[str] = Field(description="Key indicators to monitor")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    explanation: str = Field(max_length=2000)
