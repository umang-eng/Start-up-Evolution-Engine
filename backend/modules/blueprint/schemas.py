from typing import Any
from pydantic import BaseModel, Field


class ExecutiveSummary(BaseModel):
    """Pydantic model representing synthesized narrative summaries."""
    business_summary: str = Field(max_length=1500)
    strategic_summary: str = Field(max_length=1500)
    execution_summary: str = Field(max_length=1500)
    financial_summary: str = Field(max_length=1500)
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


class FundingSourceRef(BaseModel):
    """Compact reference to a funding source from the Legal & Compliance module."""
    scheme_name: str
    scheme_type: str
    amount_range: str
    application_url: str = ""
    relevance_score: float = 0.0


class RegistrationRequirementRef(BaseModel):
    """Compact reference to a registration requirement from the Legal & Compliance module."""
    requirement_name: str
    authority: str
    category: str
    is_mandatory: bool
    estimated_cost: str = ""
    priority: str = "MEDIUM"
    reference_url: str = ""


class ComplianceDirectoryRef(BaseModel):
    """Compact reference to a regulatory agency from the Legal & Compliance module."""
    agency_name: str
    jurisdiction: str
    contact_url: str = ""
    relevant_for: list[str] = Field(default_factory=list)


class LegalComplianceDoc(BaseModel):
    """Structural tables for legal & compliance documentation embedded in the Blueprint.

    Contains active grant URLs, filing requirements checklists, and local agency
    compliance directories — all grounded in real-time web search results.
    """
    funding_sources: list[FundingSourceRef] = Field(default_factory=list)
    registration_requirements: list[RegistrationRequirementRef] = Field(default_factory=list)
    compliance_directories: list[ComplianceDirectoryRef] = Field(default_factory=list)
    data_protection_requirements: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=1500)
    estimated_compliance_budget_usd: float = Field(ge=0.0, default=0.0)


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
    legal_compliance: LegalComplianceDoc = Field(
        default_factory=LegalComplianceDoc,
        description="Structural tables for legal compliance, funding schemes, and regulatory directories"
    )
