from typing import Literal
from pydantic import BaseModel, Field


class CostCategoryItem(BaseModel):
    """Pydantic model representing a single cost line item."""
    category: str = Field(description="Scope: SALARIES, INFRASTRUCTURE, LEGAL_REGISTRATION, MARKETING, SAAS_TOOLS")
    description: str = Field(max_length=300)
    monthly_usd: float = Field(ge=0.0, description="Monthly cost value")
    is_mvp_critical: bool = Field(description="Identifies if the cost is essential for the MVP launch")


class FeatureCostBreakdown(BaseModel):
    """Cost breakdown for a single feature."""
    feature_id: str = Field(description="FEAT-XXX reference")
    feature_name: str = Field(description="Human-readable feature name")
    estimated_cost_usd: float = Field(ge=0.0, description="Estimated total development cost")
    estimated_weeks: int = Field(ge=1, description="Estimated development time in weeks")
    cost_driver: str = Field(
        default="",
        max_length=200,
        description="Primary cost driver (e.g., 'complex API integration', 'ML model training')"
    )


class PhaseCostBreakdown(BaseModel):
    """Cost breakdown for a roadmap phase."""
    phase_id: str = Field(description="Phase reference ID")
    phase_name: str = Field(description="Human-readable phase name")
    estimated_cost_usd: float = Field(ge=0.0, description="Total estimated cost for this phase")
    duration_weeks: int = Field(ge=1, description="Phase duration in weeks")
    major_cost_items: list[str] = Field(
        default_factory=list,
        description="Top 2-3 cost drivers in this phase"
    )


class BudgetScenario(BaseModel):
    """Pydantic model representing a projected budget scenario."""
    name: Literal["LEAN", "BALANCED", "AGGRESSIVE"] = Field(description="Scenario target type")
    monthly_burn_usd: float = Field(ge=0.0)
    runway_months: int = Field(ge=1)
    description: str = Field(max_length=300)
    assumptions: list[str] = Field(
        default_factory=list,
        description="Key assumptions underlying this scenario"
    )


class FundingRequirement(BaseModel):
    """Capital targets, runway durations, and funding profiles."""
    minimum_target_usd: float = Field(ge=0.0)
    optimal_target_usd: float = Field(ge=0.0)
    runway_months: int = Field(ge=1)
    funding_suitability: str = Field(max_length=500, description="Funding eligibility analysis details")


class CostOutput(BaseModel):
    """Structured output returned by the Cost Estimator Module."""
    operational_costs: list[CostCategoryItem] = Field(description="Operating expenses list")
    budget_scenarios: list[BudgetScenario] = Field(description="Multi-scenario budget plans")
    funding_requirements: FundingRequirement
    mvp_cost_estimate: float = Field(ge=0.0, description="Minimum capital required to build and launch the MVP")
    year_1_cost_estimate: float = Field(ge=0.0, description="Total projected operating costs for the first year")
    financial_risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(description="Calculated financial risk level")
    feature_cost_breakdown: list[FeatureCostBreakdown] = Field(
        default_factory=list,
        description="Cost breakdown per feature from the Feature module"
    )
    phase_cost_breakdown: list[PhaseCostBreakdown] = Field(
        default_factory=list,
        description="Cost breakdown per roadmap phase"
    )
    contingency_percent: float = Field(
        ge=0.0, le=50.0, default=15.0,
        description="Contingency buffer percentage applied to total costs"
    )
    break_even_month: int | None = Field(
        default=None,
        description="Estimated month to break even (None if not estimable)"
    )
    key_cost_risks: list[str] = Field(
        default_factory=list,
        description="Risks that could cause cost overruns"
    )
    total_monthly_payroll_usd: float = Field(
        ge=0.0, default=0.0,
        description="Computed from team salaries for cross-validation"
    )
