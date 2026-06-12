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


class RoadmapPhase(BaseModel):
    """Pydantic model representing one of the 6 core development phases."""
    phase_id: str = Field(description="Slug, e.g. phase_1_validation")
    name: Literal[
        "Validation & Discovery",
        "Planning & Architecture",
        "MVP Development",
        "Testing & Feedback",
        "Launch",
        "Growth & Scaling"
    ] = Field(description="Standardized phase naming catalog")
    duration_months: int = Field(ge=1, le=6)
    milestones: list[str] = Field(description="Milestone target metrics achieved in this phase")
    tasks: list[RoadmapTask] = Field(description="Chronological task listings")


class LaunchReadinessPlan(BaseModel):
    """Maturity checklist and checklist mapping to launch readiness."""
    readiness_score: int = Field(ge=0, le=100)
    checklist: list[str] = Field(description="Operational verification check requirements")


class RoadmapOutput(BaseModel):
    """Structured output returned by the Roadmap Generator Module."""
    phases: list[RoadmapPhase] = Field(description="Standard 6-stage development timeline")
    launch_readiness_plan: LaunchReadinessPlan
