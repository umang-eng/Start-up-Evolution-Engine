"""Agent Mesh — Data contracts and type definitions.

This module defines all Pydantic models used for inter-agent communication,
tool call results, and workflow observations. No dict catch-alls — every
field is explicitly typed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Agent Roles ───────────────────────────────────────────────────

class AgentRole(str, Enum):
    """Identifies the functional role of an agent within a workflow."""
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    SYNTHESIZER = "synthesizer"
    REVIEWER = "reviewer"


# ── Tool Call Results ─────────────────────────────────────────────

class ToolCallResult(BaseModel):
    """Outcome of a single tool.execute() invocation. Never raises past the tool boundary."""
    tool_name: str
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    latency_ms: int = 0


# ── Observations (inter-agent messages) ───────────────────────────

class Observation(BaseModel):
    """An observation published by an agent to the context bus."""
    topic: str
    producer: AgentRole
    data: BaseModel
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── ResearcherAgent output ───────────────────────────────────────

class ResearchFindings(BaseModel):
    """Output of ResearcherAgent after gathering real-time data."""
    market_data: dict[str, Any] = Field(default_factory=dict)
    project_data: dict[str, Any] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    tool_errors: list[ToolCallResult] = Field(default_factory=list)


# ── AnalystAgent output ──────────────────────────────────────────

class AnalysisReport(BaseModel):
    """Output of AnalystAgent after analyzing data."""
    metrics: dict[str, float] = Field(default_factory=dict)
    patterns: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Analyst confidence in its analysis")


# ── ReviewerAgent output ─────────────────────────────────────────

class ReviewCritique(BaseModel):
    """Output of ReviewerAgent after reviewing synthesized content."""
    approved: bool
    issues: list[str] = Field(default_factory=list)
    severity: Literal["blocking", "minor", "none"] = "none"
    revision_notes: str | None = None


# ── SynthesizerAgent output is bound to existing per-stage schemas ──
# SynthesizerAgent does NOT define its own output model. Each stage's
# AgentModule binds SynthesizerAgent to the existing Pydantic schema:
#   - DNA:         backend.modules.dna.schemas.DNAOutput
#   - Features:    backend.modules.features.schemas.FeatureOutput
#   - Roadmap:     backend.modules.roadmap.schemas.RoadmapOutput
#   - Team:        backend.modules.team.schemas.TeamOutput
#   - SWOT:        backend.modules.swot.schemas.SWOTOutput
#   - Cost:        backend.modules.cost.schemas.CostOutput
#   - Blueprint:   backend.modules.blueprint.schemas.BlueprintOutput
#   - Legal:       backend.modules.legal_compliance.schemas.LegalOutput


# ── Workflow-level types ─────────────────────────────────────────

class AgentBudget(BaseModel):
    """Per-agent resource limits enforced by AgentModule."""
    max_tokens: int = 4000
    timeout_s: float = 30.0
    max_tool_calls: int = 3


class StageAgentConfig(BaseModel):
    """Configuration for a single stage's agent mesh setup."""
    enabled: bool = False
    workflow: Literal["sequential", "parallel", "debate"] = "sequential"
    agents: list[AgentRole] = Field(default_factory=list)
    max_debate_rounds: int = 2
    enable_web_research: bool = True
    budgets: dict[AgentRole, AgentBudget] = Field(default_factory=dict)
    merge_strategy: Literal["namespace", "override"] = "namespace"
