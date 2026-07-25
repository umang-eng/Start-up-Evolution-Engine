from typing import Literal
from pydantic import BaseModel, Field


class RoleCard(BaseModel):
    """Pydantic model representing an organizational role card."""
    role_id: str = Field(description="Unique slug, e.g. role_senior_backend_dev")
    title: str = Field(max_length=100)
    department: Literal[
        "Leadership",
        "Product",
        "Design",
        "Engineering",
        "AI Team",
        "Marketing & Sales",
        "Operations",
        "Customer Success"
    ] = Field(description="Target standard department placement")
    reports_to: str | None = Field(default=None, description="Role ID slug of manager, e.g. role_cto")
    responsibilities: list[str] = Field(description="Role responsibilities descriptions")
    required_skills: list[str] = Field(description="Technical or operational skill requirements")
    estimated_salary_usd: float = Field(ge=0.0, description="Projected base annual salary target")
    hiring_stage: Literal["Immediate", "Pre-MVP", "Pre-Launch", "Growth"] = Field(
        description="Chronological hiring window target"
    )
    equity_offered_percent: float = Field(
        ge=0.0, le=50.0, default=0.0,
        description="Equity percentage offered for this role (0 = cash-only)"
    )
    hiring_rationale: str = Field(
        default="", max_length=200,
        description="Why this role is needed and when"
    )


class RACIAssignment(BaseModel):
    """RACI matrix mapping role responsibilities to roadmap tasks."""
    task_id: str = Field(description="Target task slug referencing roadmap tasks")
    responsible_role_id: str = Field(description="Role ID executing task")
    accountable_role_id: str = Field(description="Role ID approving task")
    consulted_role_ids: list[str] = Field(default_factory=list, description="Role IDs consulted")
    informed_role_ids: list[str] = Field(default_factory=list, description="Role IDs informed of progress")


class TeamOutput(BaseModel):
    """Structured output returned by the Team Structure Module."""
    org_chart: list[RoleCard] = Field(
        min_length=3,
        max_length=12,
        description="Dynamic hiring pipeline (3-12 roles based on complexity)"
    )
    raci_matrix: list[RACIAssignment] = Field(description="RACI matrix assigning roles to roadmap tasks")
    recommended_team_size: int = Field(ge=1)
    hiring_sequence: list[str] = Field(description="Array of role_id slugs in priority order")
    compensation_structure: Literal["CASH_ONLY", "EQUITY_HEAVY", "BALANCED"] = Field(
        default="BALANCED",
        description="Overall compensation philosophy for this team"
    )
    equity_pool_percent: float = Field(
        ge=0.0, le=40.0, default=10.0,
        description="Total equity pool allocated for all hires (excluding founders)"
    )
    cofounder_recommendation: str = Field(
        default="",
        max_length=300,
        description="Whether a cofounder is recommended and what profile"
    )
    key_hiring_risks: list[str] = Field(
        default_factory=list,
        description="Risks in the hiring plan (e.g., 'AI talent is scarce', 'CTO role may need cofounder')"
    )
    total_monthly_payroll_usd: float = Field(
        ge=0.0, default=0.0,
        description="Total monthly payroll for cross-validation with Cost module"
    )
