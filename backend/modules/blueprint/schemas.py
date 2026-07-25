from typing import Any, Literal
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
    """Structural tables for legal & compliance documentation embedded in the Blueprint."""
    funding_sources: list[FundingSourceRef] = Field(default_factory=list)
    registration_requirements: list[RegistrationRequirementRef] = Field(default_factory=list)
    compliance_directories: list[ComplianceDirectoryRef] = Field(default_factory=list)
    data_protection_requirements: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=1500)
    estimated_compliance_budget_usd: float = Field(ge=0.0, default=0.0)


class CompetitiveAnalysis(BaseModel):
    """Competitive landscape analysis synthesized from DNA and SWOT data."""
    direct_competitors: list[str] = Field(
        default_factory=list,
        description="Companies solving the same problem for the same audience"
    )
    indirect_competitors: list[str] = Field(
        default_factory=list,
        description="Companies solving adjacent problems or different audience segments"
    )
    competitive_advantages: list[str] = Field(
        default_factory=list,
        description="Where this startup wins vs competitors"
    )
    competitive_gaps: list[str] = Field(
        default_factory=list,
        description="Areas where competitors are weak and this startup can exploit"
    )
    differentiation_strategy: str = Field(
        default="",
        max_length=500,
        description="How to position against competitors for maximum impact"
    )


class ActionItem(BaseModel):
    """A concrete next step for the founder."""
    action: str = Field(max_length=300)
    owner: Literal["FOUNDER", "CTO", "TEAM", "ADVISOR"] = Field(description="Who owns this action")
    deadline: str = Field(description="When this must be done, e.g., 'Week 1', 'Before MVP launch'")
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    depends_on: list[str] = Field(
        default_factory=list,
        description="Other actions or milestones this depends on"
    )


class ChecklistItem(BaseModel):
    """An item on the investment readiness checklist."""
    item: str = Field(description="What needs to be done")
    status: Literal["DONE", "IN_PROGRESS", "NOT_STARTED", "BLOCKED"] = Field(default="NOT_STARTED")
    importance: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(default="HIGH")


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
    competitive_analysis: CompetitiveAnalysis = Field(
        default_factory=CompetitiveAnalysis,
        description="Competitive landscape analysis — who we compete with and how we win"
    )
    market_positioning: str = Field(
        default="",
        max_length=500,
        description="One-sentence positioning statement: for [target] who [need], [product] is a [category] that [benefit]. Unlike [alternative], we [differentiator]."
    )
    investment_readiness_checklist: list[ChecklistItem] = Field(
        default_factory=list,
        description="What's needed before approaching investors"
    )
    key_assumptions: list[str] = Field(
        default_factory=list,
        description="The 3-5 assumptions that must be true for this business to work"
    )
    next_steps: list[ActionItem] = Field(
        default_factory=list,
        description="Concrete 30-day actions for the founder"
    )
    expansion_opportunities: list[str] = Field(
        default_factory=list,
        description="Adjacent markets, verticals, or product extensions to explore post-launch"
    )
    execution_risks: list[str] = Field(
        default_factory=list,
        description="Top 3-5 risks that could prevent successful execution"
    )
