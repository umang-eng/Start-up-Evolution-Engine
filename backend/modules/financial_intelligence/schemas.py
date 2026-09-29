"""Financial Intelligence Engine — investor-grade financial analysis."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from backend.modules.evidence.types import (
    ConfidenceScore, EvidenceBackedScore, EvidenceSource, FinancialMetrics
)


class FinancialProjection(BaseModel):
    """A single financial projection period."""
    period: str = Field(description="Period label (e.g., 'Year 1', 'Month 6')")
    revenue: float = Field(ge=0.0)
    costs: float = Field(ge=0.0)
    profit: float = Field(description="Revenue - Costs")
    cash_balance: float = Field(ge=0.0)
    customers: int = Field(ge=0)
    arr: float = Field(ge=0.0)
    mrr: float = Field(ge=0.0)


class UnitEconomics(BaseModel):
    """Detailed unit economics breakdown."""
    cac: float = Field(ge=0.0, description="Customer Acquisition Cost")
    ltv: float = Field(ge=0.0, description="Lifetime Value")
    ltv_cac_ratio: float = Field(ge=0.0, description="LTV/CAC ratio")
    payback_period_months: int = Field(ge=0)
    gross_margin_percent: float = Field(ge=0.0, le=100.0)
    net_margin_percent: float = Field(description="Net margin percentage")
    contribution_margin_percent: float = Field(ge=0.0, le=100.0)
    churn_rate_percent: float = Field(ge=0.0, le=100.0)
    expansion_rate_percent: float = Field(ge=0.0, description="Revenue expansion rate")
    evidence: list[EvidenceSource] = Field(default_factory=list)


class ScenarioFinancials(BaseModel):
    """Financial projections for a specific scenario."""
    scenario_name: str
    probability: float = Field(ge=0.0, le=1.0)
    year1_revenue: float = Field(ge=0.0)
    year3_revenue: float = Field(ge=0.0)
    break_even_month: int | None = Field(default=None)
    total_funding_required: float = Field(ge=0.0)
    runway_months: int = Field(ge=0)
    valuation_estimate: float = Field(ge=0.0)
    evidence: list[EvidenceSource] = Field(default_factory=list)


class FinancialIntelligenceOutput(BaseModel):
    """Complete financial intelligence output."""
    metrics: FinancialMetrics = Field(description="Core financial metrics")
    unit_economics: UnitEconomics = Field(description="Detailed unit economics")
    projections: list[FinancialProjection] = Field(min_length=1, description="Financial projections")
    scenarios: list[ScenarioFinancials] = Field(min_length=1, description="Best/Base/Worst scenarios")
    funding_requirements: dict[str, Any] = Field(description="Funding analysis")
    valuation: dict[str, Any] = Field(description="Valuation estimate")
    key_assumptions: list[str] = Field(description="Financial assumptions made")
    financial_risks: list[str] = Field(description="Key financial risks")
    recommendations: list[str] = Field(description="Financial recommendations")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(description="Confidence in financial analysis")
    explanation: str = Field(max_length=2000)
