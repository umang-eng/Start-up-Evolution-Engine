"""Agent Mesh — Multi-agent orchestration layer for the compilation pipeline.

This package implements a multi-agent system where specialized agents
(Researcher, Analyst, Synthesizer, Reviewer) collaborate to produce
higher-quality pipeline stage output than a single LLM call.
"""

from backend.agents.types import (
    AgentRole,
    ToolCallResult,
    Observation,
    ResearchFindings,
    AnalysisReport,
    ReviewCritique,
    AgentBudget,
    StageAgentConfig,
)

__all__ = [
    "AgentRole",
    "ToolCallResult",
    "Observation",
    "ResearchFindings",
    "AnalysisReport",
    "ReviewCritique",
    "AgentBudget",
    "StageAgentConfig",
]
