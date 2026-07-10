from typing import Any
from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    """Pydantic model representing synthesized narrative summaries."""
    business_summary: str = Field(max_length=5000)
    strategic_summary: str = Field(max_length=5000)
    execution_summary: str = Field(max_length=5000)
    financial_summary: str = Field(max_length=5000)
    founder_directives: list[str] = Field(description="Actionable directions list")


class StartupHealthIndicators(BaseModel):
    """Maturity and readiness indices calculated by the Health Engine."""
    composite_score: float = Field(ge=0.0, le=100.0)
    execution_readiness: float = Field(ge=0.0, le=100.0)
    funding_readiness: float = Field(ge=0.0, le=100.0)
    growth_readiness: float = Field(ge=0.0, le=100.0)
    risk_exposure: float = Field(ge=0.0, le=100.0)
    strategic_strength: float = Field(ge=0.0, le=100.0)


class ConflictResolutionLogItem(BaseModel):
    """Log entry tracking resolved multi-module data contradictions."""
    conflict_id: str
    field_path: str
    conflict_type: str
    original_values: dict[str, Any]
    resolved_value: Any
    override_rule: str
    severity: str
    log_message: str


class BlueprintOutput(BaseModel):
    """Structured output returned by the Blueprint Composer Module."""
    executive_summary: ExecutiveSummary
    startup_dna: dict[str, Any] = Field(description="Normalized Startup DNA payload")
    product_architecture: dict[str, Any] = Field(description="Normalized Product Feature specifications")
    execution_roadmap: dict[str, Any] = Field(description="Normalized Project Timeline milestones")
    team_structure: dict[str, Any] = Field(description="Normalized Hiring structures")
    swot_analysis: dict[str, Any] = Field(description="Normalized SWOT Risk Opportunity profile")
    financial_plan: dict[str, Any] = Field(description="Normalized Projections and operational tools budget")
    health_indicators: StartupHealthIndicators
    conflict_resolution_log: list[ConflictResolutionLogItem] = Field(default_factory=list)
