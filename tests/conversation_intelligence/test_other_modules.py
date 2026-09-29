"""Tests for meeting health, conflict detection, action execution, and other modules."""

import pytest
from backend.modules.meeting_health.engine import (
    MeetingHealthEngine, MeetingHealthReport, HealthDimension
)
from backend.modules.conflict_detection.engine import (
    ConflictDetectionEngine, DetectedConflict, ConflictSeverity, ConflictDetectionResult
)
from backend.modules.action_execution.engine import (
    ActionExecutionEngine, GeneratedTask, TaskPlatform, TaskPriority, ActionExtractionResult
)
from backend.modules.meeting_timeline.engine import (
    TimelineEngine, TimelineEvent, TimelineEventType, CompanyTimeline
)
from backend.modules.investor_mode.engine import (
    InvestorModeEngine, InvestorAnalysis, InvestorQuestion
)
from backend.modules.pitch_intelligence.engine import (
    PitchIntelligenceEngine, PitchAnalysis, PitchMetric
)
from backend.modules.meeting_sync.engine import (
    BlueprintSyncEngine, BlueprintSyncResult, PipelineChange, ChangeType
)
from backend.modules.memory.types import MemoryEntry, MemoryType


class TestMeetingHealth:
    def test_engine_initialization(self):
        engine = MeetingHealthEngine()
        assert len(engine.reports) == 0

    def test_fallback_report(self):
        engine = MeetingHealthEngine()
        report = engine._fallback_report("meeting-001")
        assert report.meeting_id == "meeting-001"
        assert report.overall_score == 5.0
        assert len(report.dimensions) == 9

    def test_get_trend(self):
        engine = MeetingHealthEngine()
        trend = engine.get_trend()
        assert trend["trend"] == "no_data"

    def test_health_dimension(self):
        dim = HealthDimension(
            name="Focus",
            score=8.0,
            weight=1.0,
            explanation="Very focused meeting",
            improvement="None needed",
        )
        assert dim.name == "Focus"
        assert dim.score == 8.0


class TestConflictDetection:
    def test_engine_initialization(self):
        engine = ConflictDetectionEngine()
        assert len(engine.all_conflicts) == 0

    def test_conflict_severity(self):
        assert ConflictSeverity.LOW == "low"
        assert ConflictSeverity.HIGH == "high"

    def test_detected_conflict(self):
        conflict = DetectedConflict(
            topic="Database choice",
            party_a="CTO",
            party_a_view="PostgreSQL",
            party_b="Lead Dev",
            party_b_view="MongoDB",
            severity=ConflictSeverity.MEDIUM,
            resolution_status="unresolved",
        )
        assert conflict.topic == "Database choice"
        assert conflict.severity == ConflictSeverity.MEDIUM

    def test_get_unresolved(self):
        engine = ConflictDetectionEngine()
        engine.all_conflicts.append(DetectedConflict(
            topic="Test", party_a="A", party_a_view="X",
            party_b="B", party_b_view="Y",
            severity=ConflictSeverity.LOW,
            resolution_status="unresolved",
        ))
        unresolved = engine.get_unresolved()
        assert len(unresolved) == 1

    def test_get_by_severity(self):
        engine = ConflictDetectionEngine()
        engine.all_conflicts.append(DetectedConflict(
            topic="Critical issue", party_a="A", party_a_view="X",
            party_b="B", party_b_view="Y",
            severity=ConflictSeverity.CRITICAL,
            resolution_status="unresolved",
        ))
        critical = engine.get_by_severity(ConflictSeverity.CRITICAL)
        assert len(critical) == 1


class TestActionExecution:
    def test_engine_initialization(self):
        engine = ActionExecutionEngine()
        assert len(engine.all_tasks) == 0

    def test_generated_task(self):
        task = GeneratedTask(
            title="Set up CI/CD",
            description="Configure GitHub Actions for automated testing",
            platform=TaskPlatform.GITHUB,
            owner="DevOps",
            priority=TaskPriority.HIGH,
            deadline="2026-02-01",
            related_meeting_id="m1",
        )
        assert task.title == "Set up CI/CD"
        assert task.platform == TaskPlatform.GITHUB

    def test_to_github_issue(self):
        engine = ActionExecutionEngine()
        task = GeneratedTask(
            title="Fix bug", description="Fix login issue",
            platform=TaskPlatform.GITHUB, owner="Dev",
            priority=TaskPriority.HIGH, related_meeting_id="m1",
        )
        issue = engine.to_github_issue(task)
        assert issue["title"] == "Fix bug"

    def test_to_jira_task(self):
        engine = ActionExecutionEngine()
        task = GeneratedTask(
            title="Design UI", description="Create mockups",
            platform=TaskPlatform.JIRA, owner="Designer",
            priority=TaskPriority.MEDIUM, related_meeting_id="m1",
        )
        jira = engine.to_jira_task(task)
        assert jira["fields"]["summary"] == "Design UI"

    def test_get_summary(self):
        engine = ActionExecutionEngine()
        engine.all_tasks.append(GeneratedTask(
            title="Task 1", description="Desc",
            platform=TaskPlatform.GITHUB, owner="Dev",
            priority=TaskPriority.HIGH, related_meeting_id="m1",
        ))
        summary = engine.get_summary()
        assert summary["total"] == 1


class TestMeetingTimeline:
    def test_engine_initialization(self):
        engine = TimelineEngine(project_id="proj-001")
        assert engine.project_id == "proj-001"

    def test_timeline_event_types(self):
        for event_type in TimelineEventType:
            event = TimelineEvent(
                event_type=event_type,
                title=f"Test {event_type.value}",
                description="Test",
                date="2026-01-01",
                meeting_id="m1",
            )
            assert event.event_type == event_type

    def test_get_by_type(self):
        engine = TimelineEngine(project_id="proj-001")
        engine.timeline.events.append(TimelineEvent(
            event_type=TimelineEventType.DECISION,
            title="Decision", description="Test",
            date="2026-01-01", meeting_id="m1",
        ))
        decisions = engine.get_by_type(TimelineEventType.DECISION)
        assert len(decisions) == 1

    def test_get_summary(self):
        engine = TimelineEngine(project_id="proj-001")
        event = TimelineEvent(
            event_type=TimelineEventType.HIRE,
            title="New hire", description="Hired CTO",
            date="2026-01-01", meeting_id="m1",
        )
        engine.timeline.events.append(event)
        engine.timeline.total_events = len(engine.timeline.events)
        summary = engine.get_summary()
        assert summary["total_events"] == 1


class TestInvestorMode:
    def test_engine_initialization(self):
        engine = InvestorModeEngine()
        assert len(engine.analyses) == 0

    def test_investor_analysis(self):
        analysis = InvestorAnalysis(
            meeting_id="m1",
            is_investor_meeting=True,
            investor_type="VC",
            likely_questions=[],
            strengths=["Strong team"],
            weaknesses=["Unproven market"],
            objections=[],
            missing_metrics=["CAC"],
            due_diligence_requests=[],
            funding_probability=0.6,
            follow_up_recommendations=[],
            investor_action_plan=[],
            summary="Promising but needs validation",
        )
        assert analysis.is_investor_meeting is True
        assert analysis.funding_probability == 0.6


class TestPitchIntelligence:
    def test_engine_initialization(self):
        engine = PitchIntelligenceEngine()
        assert len(engine.analyses) == 0

    def test_pitch_metric(self):
        metric = PitchMetric(
            name="Speaking Pace",
            score=7.0,
            value="145 wpm",
            benchmark="130-150 wpm",
            explanation="Good pace",
            coaching_tip="Maintain current pace",
        )
        assert metric.name == "Speaking Pace"
        assert metric.score == 7.0

    def test_get_improvement_trend(self):
        engine = PitchIntelligenceEngine()
        trend = engine.get_improvement_trend()
        assert trend["trend"] == "insufficient_data"


class TestBlueprintSync:
    def test_engine_initialization(self):
        engine = BlueprintSyncEngine(project_id="proj-001")
        assert engine.project_id == "proj-001"

    def test_pipeline_change(self):
        change = PipelineChange(
            stage_name="features",
            change_type=ChangeType.MODIFIED,
            description="Added new feature",
            confidence=0.8,
        )
        assert change.stage_name == "features"
        assert change.change_type == ChangeType.MODIFIED

    def test_cascading_changes(self):
        engine = BlueprintSyncEngine(project_id="proj-001")
        cascading = engine._compute_cascading_changes({"dna"})
        assert "features" in cascading
        assert "roadmap" in cascading

    def test_version_increment(self):
        engine = BlueprintSyncEngine(project_id="proj-001")
        changes = [PipelineChange(
            stage_name="dna", change_type=ChangeType.MODIFIED,
            description="Major change", confidence=0.9,
            priority="CRITICAL",
        )]
        version = engine._determine_version_increment(changes)
        assert version == "major"
