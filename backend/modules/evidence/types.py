"""Evidence and Confidence types — the foundation for evidence-driven intelligence.

Every claim, score, and recommendation in the pipeline must be backed by
structured evidence with source tracking, confidence scores, and
explainability metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class EvidenceSource(BaseModel):
    """A single piece of evidence from a specific source."""
    source_name: str = Field(description="Name of the source (e.g., 'Statista', 'Crunchbase', 'Gartner')")
    source_url: str = Field(default="", description="URL or reference identifier")
    source_type: Literal["WEB_SEARCH", "DATABASE", "LLM_KNOWLEDGE", "USER_INPUT", "CALCULATION", "API"] = Field(
        description="How this evidence was obtained"
    )
    retrieval_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        description="When this evidence was retrieved (ISO date)"
    )
    snippet: str = Field(default="", max_length=500, description="Relevant excerpt from the source")
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.8, description="How relevant this evidence is to the claim")


class ConfidenceScore(BaseModel):
    """Confidence assessment for any claim or score."""
    score: float = Field(ge=0.0, le=100.0, description="Confidence percentage (0-100)")
    evidence: list[EvidenceSource] = Field(default_factory=list, description="Supporting evidence")
    missing_information: list[str] = Field(
        default_factory=list,
        description="What information would increase confidence"
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made when evidence was incomplete"
    )
    alternative_interpretations: list[str] = Field(
        default_factory=list,
        description="Other ways the data could be interpreted"
    )

    @property
    def confidence_level(self) -> str:
        if self.score >= 80:
            return "HIGH"
        elif self.score >= 60:
            return "MEDIUM"
        elif self.score >= 40:
            return "LOW"
        return "VERY_LOW"


class EvidenceBackedScore(BaseModel):
    """A score that is always backed by evidence and confidence."""
    value: float = Field(description="The actual score value")
    label: str = Field(description="What this score represents")
    confidence: ConfidenceScore = Field(description="Confidence assessment with evidence")
    explanation: str = Field(
        default="",
        max_length=1000,
        description="Why this score was given, citing specific evidence"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "label": self.label,
            "confidence": self.confidence.score,
            "confidence_level": self.confidence.confidence_level,
            "evidence_count": len(self.confidence.evidence),
            "explanation": self.explanation,
        }


class ExplainableDecision(BaseModel):
    """A decision with full explainability."""
    decision: str = Field(description="The decision or recommendation")
    rationale: str = Field(max_length=1000, description="Why this decision was made")
    evidence: list[EvidenceSource] = Field(default_factory=list, description="Supporting evidence")
    assumptions: list[str] = Field(default_factory=list, description="Key assumptions")
    alternatives_rejected: list[str] = Field(
        default_factory=list,
        description="Other options that were considered and rejected"
    )
    what_would_change_it: list[str] = Field(
        default_factory=list,
        description="What new information would change this decision"
    )
    confidence: float = Field(ge=0.0, le=100.0, default=50.0, description="Confidence in this decision")


class ScenarioAnalysis(BaseModel):
    """A stress-tested scenario with impact assessment."""
    scenario_name: str = Field(description="Name of the scenario")
    description: str = Field(max_length=500, description="What happens in this scenario")
    impact: Literal["CATASTROPHIC", "SEVERE", "MODERATE", "MINOR", "NEGLIGIBLE"] = Field(
        description="Business impact level"
    )
    probability: float = Field(ge=0.0, le=1.0, description="Probability of this scenario occurring")
    impact_score: float = Field(ge=0.0, le=10.0, description="Numerical impact score (0=no impact, 10=existential)")
    mitigation_strategy: str = Field(max_length=500, description="How to mitigate this scenario")
    recovery_plan: str = Field(max_length=500, description="How to recover if this occurs")
    expected_outcome: str = Field(max_length=300, description="Expected business outcome")
    evidence: list[EvidenceSource] = Field(default_factory=list, description="Evidence supporting this assessment")


class MoatAssessment(BaseModel):
    """Assessment of a specific competitive moat type."""
    moat_type: str = Field(description="Type of moat (e.g., 'Network Effects', 'Data Moat')")
    strength: float = Field(ge=0.0, le=10.0, description="Strength of this moat (0=none, 10=fortress)")
    evidence: list[EvidenceSource] = Field(default_factory=list, description="Evidence supporting this assessment")
    difficulty_to_copy: Literal["TRIVIAL", "EASY", "MODERATE", "HARD", "NEAR_IMPOSSIBLE"] = Field(
        description="How hard for competitors to replicate"
    )
    time_to_copy_months: int = Field(ge=0, description="Estimated months for a well-funded competitor to replicate")
    cost_to_copy_usd: float = Field(ge=0.0, description="Estimated cost to replicate in USD")
    explanation: str = Field(max_length=500, description="Why this moat exists and how strong it is")


class FinancialMetrics(BaseModel):
    """Investor-grade financial metrics."""
    arr: float = Field(ge=0.0, description="Annual Recurring Revenue")
    mrr: float = Field(ge=0.0, description="Monthly Recurring Revenue")
    gross_margin_percent: float = Field(ge=0.0, le=100.0, description="Gross margin percentage")
    cac: float = Field(ge=0.0, description="Customer Acquisition Cost")
    ltv: float = Field(ge=0.0, description="Lifetime Value")
    ltv_cac_ratio: float = Field(ge=0.0, description="LTV/CAC ratio")
    burn_rate: float = Field(ge=0.0, description="Monthly burn rate")
    burn_multiple: float = Field(ge=0.0, description="Burn multiple (burn / net new ARR)")
    payback_period_months: int = Field(ge=0, description="Months to recover CAC")
    cash_runway_months: int = Field(ge=0, description="Months of cash remaining")
    break_even_month: int | None = Field(default=None, description="Month to break even")
    assumptions: list[str] = Field(default_factory=list, description="Key financial assumptions")
    evidence: list[EvidenceSource] = Field(default_factory=list, description="Evidence supporting calculations")


class InvestorRecommendation(BaseModel):
    """Investment Committee recommendation."""
    recommendation: Literal["STRONG_INVEST", "INVEST", "CONDITIONAL_INVEST", "PASS", "STRONG_PASS"] = Field(
        description="Final investment recommendation"
    )
    investment_thesis: str = Field(max_length=1000, description="Core investment thesis")
    reasons_to_invest: list[str] = Field(min_length=1, description="Key reasons to invest")
    reasons_not_to_invest: list[str] = Field(min_length=1, description="Key risks or concerns")
    fatal_risks: list[str] = Field(default_factory=list, description="Risks that could kill the company")
    biggest_unknowns: list[str] = Field(default_factory=list, description="What we don't know")
    competitive_advantages: list[str] = Field(default_factory=list, description="Key advantages")
    exit_opportunities: list[str] = Field(default_factory=list, description="Potential exit paths")
    expected_roi: str = Field(default="", description="Expected return on investment range")
    confidence: ConfidenceScore = Field(description="Confidence in this recommendation")
    due_diligence_checklist: list[str] = Field(
        default_factory=list,
        description="Items to verify before final decision"
    )
