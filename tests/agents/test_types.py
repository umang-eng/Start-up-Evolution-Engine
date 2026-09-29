"""Unit tests for backend.agents.types — Pydantic contract validation.

These tests verify that every model in types.py enforces its constraints.
No live network calls, no fixtures beyond inline data.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

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


# ── AgentRole ─────────────────────────────────────────────────────

class TestAgentRole:
    def test_all_roles_exist(self):
        assert set(AgentRole) == {
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.SYNTHESIZER,
            AgentRole.REVIEWER,
        }

    def test_string_values(self):
        assert AgentRole.RESEARCHER == "researcher"
        assert AgentRole.ANALYST == "analyst"
        assert AgentRole.SYNTHESIZER == "synthesizer"
        assert AgentRole.REVIEWER == "reviewer"


# ── ToolCallResult ───────────────────────────────────────────────

class TestToolCallResult:
    def test_success_result(self):
        result = ToolCallResult(
            tool_name="web_search",
            ok=True,
            data={"results": ["r1", "r2"]},
            latency_ms=150,
        )
        assert result.ok is True
        assert result.error is None
        assert result.data == {"results": ["r1", "r2"]}
        assert result.latency_ms == 150

    def test_failure_result(self):
        result = ToolCallResult(
            tool_name="web_search",
            ok=False,
            error="Timeout after 30s",
            latency_ms=30000,
        )
        assert result.ok is False
        assert result.error == "Timeout after 30s"
        assert result.data is None

    def test_defaults(self):
        result = ToolCallResult(tool_name="db_query", ok=True)
        assert result.latency_ms == 0
        assert result.data is None
        assert result.error is None


# ── Observation ───────────────────────────────────────────────────

class TestObservation:
    def test_create_with_research_findings(self):
        findings = ResearchFindings(
            market_data={"tam": "50B"},
            project_data={"title": "TestCo"},
            sources=["https://example.com"],
        )
        obs = Observation(
            topic="research_complete",
            producer=AgentRole.RESEARCHER,
            data=findings,
        )
        assert obs.topic == "research_complete"
        assert obs.producer == AgentRole.RESEARCHER
        assert isinstance(obs.created_at, datetime)
        assert obs.data.market_data == {"tam": "50B"}

    def test_default_timestamp(self):
        findings = ResearchFindings()
        obs = Observation(
            topic="test",
            producer=AgentRole.ANALYST,
            data=findings,
        )
        assert obs.created_at.tzinfo is not None


# ── ResearchFindings ─────────────────────────────────────────────

class TestResearchFindings:
    def test_empty_defaults(self):
        rf = ResearchFindings()
        assert rf.market_data == {}
        assert rf.project_data == {}
        assert rf.sources == []
        assert rf.tool_errors == []

    def test_with_tool_errors(self):
        err = ToolCallResult(tool_name="search", ok=False, error="rate limited")
        rf = ResearchFindings(tool_errors=[err])
        assert len(rf.tool_errors) == 1
        assert rf.tool_errors[0].ok is False


# ── AnalysisReport ───────────────────────────────────────────────

class TestAnalysisReport:
    def test_valid_confidence(self):
        report = AnalysisReport(
            metrics={"market_fit": 0.85},
            patterns=["Strong growth trend"],
            confidence=0.9,
        )
        assert report.confidence == 0.9
        assert report.metrics["market_fit"] == 0.85

    def test_confidence_boundary_zero(self):
        report = AnalysisReport(confidence=0.0)
        assert report.confidence == 0.0

    def test_confidence_boundary_one(self):
        report = AnalysisReport(confidence=1.0)
        assert report.confidence == 1.0

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            AnalysisReport(confidence=1.5)

    def test_confidence_negative(self):
        with pytest.raises(ValidationError):
            AnalysisReport(confidence=-0.1)


# ── ReviewCritique ───────────────────────────────────────────────

class TestReviewCritique:
    def test_approved(self):
        critique = ReviewCritique(
            approved=True,
            issues=[],
            severity="none",
        )
        assert critique.approved is True
        assert critique.severity == "none"

    def test_blocking_issues(self):
        critique = ReviewCritique(
            approved=False,
            issues=["Missing executive summary", "Scores inconsistent"],
            severity="blocking",
            revision_notes="Must address all issues before approval",
        )
        assert critique.approved is False
        assert len(critique.issues) == 2
        assert critique.severity == "blocking"

    def test_minor_issues(self):
        critique = ReviewCritique(
            approved=True,
            issues=["Minor typo in summary"],
            severity="minor",
        )
        assert critique.approved is True
        assert critique.severity == "minor"


# ── AgentBudget ──────────────────────────────────────────────────

class TestAgentBudget:
    def test_defaults(self):
        budget = AgentBudget()
        assert budget.max_tokens == 4000
        assert budget.timeout_s == 30.0
        assert budget.max_tool_calls == 3

    def test_custom(self):
        budget = AgentBudget(max_tokens=8000, timeout_s=60.0, max_tool_calls=10)
        assert budget.max_tokens == 8000
        assert budget.timeout_s == 60.0
        assert budget.max_tool_calls == 10


# ── StageAgentConfig ─────────────────────────────────────────────

class TestStageAgentConfig:
    def test_disabled_by_default(self):
        config = StageAgentConfig()
        assert config.enabled is False
        assert config.workflow == "sequential"
        assert config.agents == []
        assert config.max_debate_rounds == 2
        assert config.enable_web_research is True
        assert config.merge_strategy == "namespace"

    def test_full_config(self):
        config = StageAgentConfig(
            enabled=True,
            workflow="debate",
            agents=[AgentRole.RESEARCHER, AgentRole.SYNTHESIZER, AgentRole.REVIEWER],
            max_debate_rounds=3,
            enable_web_research=True,
            budgets={
                AgentRole.RESEARCHER: AgentBudget(max_tool_calls=5),
            },
            merge_strategy="override",
        )
        assert config.enabled is True
        assert config.workflow == "debate"
        assert len(config.agents) == 3
        assert config.budgets[AgentRole.RESEARCHER].max_tool_calls == 5
