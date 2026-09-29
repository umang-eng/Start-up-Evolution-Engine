"""Product Execution Engine — generates PRDs, architecture, sprints, and release plans."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from backend.modules.evidence.types import ConfidenceScore, EvidenceSource


class UserStory(BaseModel):
    """A single user story with acceptance criteria."""
    id: str = Field(description="Story ID (e.g., US-001)")
    title: str = Field(description="Story title")
    user_type: str = Field(description="Who is the user")
    action: str = Field(description="What they want to do")
    benefit: str = Field(description="Why they want to do it")
    acceptance_criteria: list[str] = Field(min_length=1, description="Definition of done")
    priority: str = Field(description="P0/P1/P2/P3")
    effort_estimate: str = Field(description="XS/S/M/L/XL")
    feature_id: str = Field(default="", description="Linked feature ID")


class SprintBacklog(BaseModel):
    """A single sprint's backlog."""
    sprint_number: int
    sprint_name: str
    duration_weeks: int = Field(default=2)
    goal: str = Field(description="Sprint goal")
    stories: list[UserStory] = Field(description="Stories in this sprint")
    total_effort_points: int = Field(ge=0)
    risks: list[str] = Field(default_factory=list)


class TechnicalArchitecture(BaseModel):
    """Technical architecture design."""
    system_overview: str = Field(max_length=1000, description="High-level system overview")
    components: list[dict[str, str]] = Field(description="System components with descriptions")
    data_flow: str = Field(max_length=500, description="How data flows through the system")
    api_endpoints: list[dict[str, str]] = Field(description="API endpoint designs")
    database_schema: list[dict[str, str]] = Field(description="Database table designs")
    infrastructure: str = Field(max_length=500, description="Infrastructure requirements")
    security_considerations: list[str] = Field(description="Security requirements")


class ReleasePlan(BaseModel):
    """Release plan with milestones."""
    release_name: str
    version: str
    target_date: str
    features: list[str] = Field(description="Features included")
    milestones: list[dict[str, str]] = Field(description="Key milestones")
    success_metrics: list[str] = Field(description="How to measure success")
    rollback_plan: str = Field(description="How to rollback if needed")


class ProductExecutionOutput(BaseModel):
    """Complete product execution output."""
    product_vision: str = Field(max_length=1000, description="Product vision statement")
    prd_summary: str = Field(max_length=2000, description="PRD executive summary")
    user_stories: list[UserStory] = Field(default_factory=list, description="All user stories")
    technical_architecture: TechnicalArchitecture = Field(description="Architecture design")
    sprints: list[SprintBacklog] = Field(default_factory=list, description="Sprint plan")
    release_plan: ReleasePlan = Field(description="Release plan")
    qa_strategy: list[str] = Field(description="QA approach")
    deployment_strategy: list[str] = Field(description="Deployment approach")
    evidence: list[EvidenceSource] = Field(default_factory=list)
    confidence: ConfidenceScore = Field(description="Confidence in execution plan")
    explanation: str = Field(max_length=2000)
