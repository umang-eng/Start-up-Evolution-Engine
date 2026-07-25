"""Tests for decision intelligence system."""

import pytest
from backend.modules.decisions.engine import (
    Decision, DecisionLog, DecisionStatus, DecisionExtractionResult, DecisionIntelligence
)


class TestDecision:
    def test_create_decision(self):
        decision = Decision(
            decision="Use PostgreSQL as primary database",
            reason="Better JSON support and async capabilities",
            supporting_evidence=["Team experience", "Performance benchmarks"],
            participants=["CTO", "Lead Dev"],
            confidence=0.9,
            alternatives_rejected=["MongoDB - less ACID compliance"],
            impacted_modules=["blueprint", "cost"],
            follow_up_actions=["Set up database", "Create schema"],
            category="technical",
            source_meeting_id="meeting-001",
        )
        assert decision.decision == "Use PostgreSQL as primary database"
        assert decision.confidence == 0.9
        assert decision.status == DecisionStatus.ACCEPTED
        assert len(decision.follow_up_actions) == 2

    def test_decision_statuses(self):
        for status in DecisionStatus:
            decision = Decision(
                decision="Test",
                reason="Test",
                confidence=0.5,
                source_meeting_id="test",
                status=status,
            )
            assert decision.status == status


class TestDecisionLog:
    def test_create_log(self):
        log = DecisionLog(project_id="proj-001")
        assert log.project_id == "proj-001"
        assert log.total_decisions == 0


class TestDecisionIntelligence:
    def test_initialization(self):
        engine = DecisionIntelligence(project_id="proj-001")
        assert engine.project_id == "proj-001"
        assert engine.log.project_id == "proj-001"

    def test_get_recent(self):
        engine = DecisionIntelligence(project_id="proj-001")
        for i in range(5):
            engine.log.decisions.append(Decision(
                decision=f"Decision {i}",
                reason=f"Reason {i}",
                confidence=0.8,
                source_meeting_id=f"m{i}",
            ))
        recent = engine.get_recent(limit=3)
        assert len(recent) == 3

    def test_search(self):
        engine = DecisionIntelligence(project_id="proj-001")
        engine.log.decisions.append(Decision(
            decision="Use React for frontend",
            reason="Team expertise",
            confidence=0.9,
            source_meeting_id="m1",
        ))
        results = engine.search("React")
        assert len(results) == 1

    def test_get_pending_actions(self):
        engine = DecisionIntelligence(project_id="proj-001")
        engine.log.decisions.append(Decision(
            decision="Launch beta",
            reason="Ready for testing",
            confidence=0.8,
            source_meeting_id="m1",
            follow_up_actions=["Set up beta environment", "Invite users"],
        ))
        pending = engine.get_pending_actions()
        assert len(pending) == 1
