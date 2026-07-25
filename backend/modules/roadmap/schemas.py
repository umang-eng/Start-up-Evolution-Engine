from typing import Literal
from pydantic import BaseModel, Field


class RoadmapTask(BaseModel):
    """Pydantic model representing a single task in a phase."""
    id: str = Field(description="Deterministic slug, e.g. task_api_routes")
    title: str = Field(max_length=100)
    description: str = Field(max_length=300)
    duration_weeks: int = Field(ge=1, le=12)
    assigned_role_id: str = Field(description="Target developer/hiring role slug, e.g. role_senior_dev")
    dependencies: list[str] = Field(default_factory=list, description="List of upstream task IDs")
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        default="MEDIUM",
        description="Risk level for this specific task"
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Definition of done — what must be true for this task to be complete"
    )
    feature_ids: list[str] = Field(
        default_factory=list,
        description="FEAT-XXX IDs this task implements"
    )
    is_critical_path: bool = Field(
        default=False,
        description="Whether this task is on the critical path (delay = project delay)"
    )


class RoadmapPhase(BaseModel):
    """Pydantic model representing one development phase."""
    phase_id: str = Field(description="Slug, e.g. phase_1_validation")
    name: str = Field(
        max_length=100,
        description="Phase name, e.g., 'Validation & Discovery', 'MVP Development', 'Growth & Scaling'"
    )
    duration_months: int = Field(ge=1, le=6)
    milestones: list[str] = Field(description="Milestone target metrics achieved in this phase")
    tasks: list[RoadmapTask] = Field(description="Chronological task listings")
    phase_objective: str = Field(
        default="",
        max_length=300,
        description="Primary objective of this phase"
    )
    key_risks: list[str] = Field(
        default_factory=list,
        description="Risks specific to this phase"
    )


class LaunchReadinessPlan(BaseModel):
    """Maturity checklist and checklist mapping to launch readiness."""
    readiness_score: int = Field(ge=0, le=100)
    checklist: list[str] = Field(description="Operational verification check requirements")


class RoadmapOutput(BaseModel):
    """Structured output returned by the Roadmap Generator Module."""
    phases: list[RoadmapPhase] = Field(
        min_length=3,
        max_length=8,
        description="Dynamic development timeline (3-8 phases based on complexity)"
    )
    launch_readiness_plan: LaunchReadinessPlan
    total_estimated_weeks: int = Field(
        ge=1,
        description="Total estimated project duration in weeks"
    )
    critical_path: list[str] = Field(
        default_factory=list,
        description="Task IDs on the critical path — these cannot slip without delaying launch"
    )
    key_dependencies: list[str] = Field(
        default_factory=list,
        description="Cross-phase dependency risks that could cause cascading delays"
    )
