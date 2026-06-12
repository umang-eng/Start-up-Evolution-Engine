from typing import Literal
from pydantic import BaseModel, Field


class CostCategoryItem(BaseModel):
    """Pydantic model representing a single cost line item."""
    category: str = Field(description="Scope: SALARIES, INFRASTRUCTURE, LEGAL_REGISTRATION, MARKETING, SAAS_TOOLS")
    description: str = Field(max_length=300)
    monthly_usd: float = Field(ge=0.0, description="Monthly cost value")
    is_mvp_critical: bool = Field(description="Identifies if the cost is essential for the MVP launch")


class BudgetScenario(BaseModel):
    """Pydantic model representing a projected budget scenario."""
    name: Literal["LEAN", "BALANCED", "AGGRESSIVE"] = Field(description="Scenario target type")
    monthly_burn_usd: float = Field(ge=0.0)
    runway_months: int = Field(ge=1)
    description: str = Field(max_length=300)


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
