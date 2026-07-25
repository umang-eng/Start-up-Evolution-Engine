"""Tests for investment committee simulation."""

import pytest
from backend.modules.investment_committee.schemas import (
    InvestmentCommitteeOutput, CommitteeMember
)
from backend.modules.evidence.types import ConfidenceScore, InvestorRecommendation


class TestCommitteeMember:
    def test_create_member(self):
        member = CommitteeMember(
            name="Sarah Chen",
            firm="Horizon Ventures",
            thesis="Strong team in growing market",
            vote="INVEST",
            confidence=80.0,
            key_concern="Market timing",
            key_excitement="Technical moat",
            suggested_terms="$2M at $8M pre-money",
        )
        assert member.name == "Sarah Chen"
        assert member.vote == "INVEST"
        assert member.confidence == 80.0


class TestInvestmentCommitteeOutput:
    def test_create_output(self):
        member = CommitteeMember(
            name="Test Partner", firm="Test VC",
            thesis="Test thesis", vote="INVEST",
            confidence=75.0, key_concern="Test concern",
            key_excitement="Test excitement",
            suggested_terms="Test terms",
        )
        output = InvestmentCommitteeOutput(
            recommendation=InvestorRecommendation(
                recommendation="INVEST",
                investment_thesis="Strong opportunity",
                reasons_to_invest=["Large market"],
                reasons_not_to_invest=["Unproven"],
                confidence=ConfidenceScore(score=70.0),
                due_diligence_checklist=["Customer references"],
            ),
            committee_members=[member],
            vote_tally={"INVEST": 3, "PASS": 1, "CONDITIONAL": 1},
            deliberation_notes=["Strong team noted"],
            term_sheet={"pre_money": 8000000},
            due_diligence_status={"Financial audit": "PENDING"},
            confidence=ConfidenceScore(score=70.0),
            explanation="IC simulation complete",
        )
        assert output.recommendation.recommendation == "INVEST"
        assert len(output.committee_members) == 1


class TestInvestmentCommitteeModule:
    @pytest.mark.asyncio
    async def test_module_initialization(self):
        from backend.modules.investment_committee.module import InvestmentCommitteeModule
        module = InvestmentCommitteeModule()
        assert module.stage_name == "investment_committee"
        assert "financial_intelligence" in module.input_stages

    @pytest.mark.asyncio
    async def test_fallback_output(self):
        from backend.modules.investment_committee.module import InvestmentCommitteeModule
        module = InvestmentCommitteeModule()
        output = module._fallback_output([], 25000)
        assert isinstance(output, InvestmentCommitteeOutput)
        assert output.recommendation.recommendation == "CONDITIONAL_INVEST"
