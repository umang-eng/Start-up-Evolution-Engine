"""Tests for evidence and confidence infrastructure."""

import pytest
from backend.modules.evidence.types import (
    EvidenceSource, ConfidenceScore, EvidenceBackedScore,
    ExplainableDecision, ScenarioAnalysis, MoatAssessment,
    FinancialMetrics, InvestorRecommendation
)


class TestEvidenceSource:
    def test_create_evidence_source(self):
        source = EvidenceSource(
            source_name="Statista",
            source_url="https://statista.com/market-data",
            source_type="WEB_SEARCH",
            snippet="Market size reached $50B in 2025",
            relevance_score=0.9,
        )
        assert source.source_name == "Statista"
        assert source.source_type == "WEB_SEARCH"
        assert source.relevance_score == 0.9

    def test_evidence_source_default_date(self):
        source = EvidenceSource(
            source_name="Test",
            source_type="LLM_KNOWLEDGE",
        )
        assert source.retrieval_date is not None
        assert len(source.retrieval_date) == 10  # YYYY-MM-DD


class TestConfidenceScore:
    def test_confidence_levels(self):
        high = ConfidenceScore(score=85.0)
        assert high.confidence_level == "HIGH"

        medium = ConfidenceScore(score=65.0)
        assert medium.confidence_level == "MEDIUM"

        low = ConfidenceScore(score=45.0)
        assert low.confidence_level == "LOW"

        very_low = ConfidenceScore(score=20.0)
        assert very_low.confidence_level == "VERY_LOW"

    def test_confidence_with_evidence(self):
        evidence = EvidenceSource(
            source_name="Test", source_type="WEB_SEARCH",
            snippet="Test snippet",
        )
        conf = ConfidenceScore(
            score=75.0,
            evidence=[evidence],
            missing_information=["More data needed"],
            assumptions=["Market is stable"],
        )
        assert len(conf.evidence) == 1
        assert conf.confidence_level == "MEDIUM"


class TestEvidenceBackedScore:
    def test_to_dict(self):
        score = EvidenceBackedScore(
            value=85.0,
            label="Market Opportunity",
            confidence=ConfidenceScore(score=80.0),
            explanation="Strong market signals",
        )
        d = score.to_dict()
        assert d["value"] == 85.0
        assert d["label"] == "Market Opportunity"
        assert d["confidence"] == 80.0
        assert d["confidence_level"] == "HIGH"
        assert d["explanation"] == "Strong market signals"


class TestExplainableDecision:
    def test_explainable_decision(self):
        decision = ExplainableDecision(
            decision="Enter the market",
            rationale="Strong market signals and low competition",
            assumptions=["Market data is accurate"],
            alternatives_rejected=["Wait for market to mature"],
            what_would_change_it=["New competitor with 10x funding"],
            confidence=75.0,
        )
        assert decision.decision == "Enter the market"
        assert decision.confidence == 75.0
        assert len(decision.alternatives_rejected) == 1


class TestScenarioAnalysis:
    def test_scenario_analysis(self):
        scenario = ScenarioAnalysis(
            scenario_name="Competitor Entry",
            description="Large tech company enters the market",
            impact="SEVERE",
            probability=0.4,
            impact_score=7.5,
            mitigation_strategy="Build switching costs",
            recovery_plan="Differentiate on niche features",
            expected_outcome="Reduced growth but survival",
        )
        assert scenario.impact == "SEVERE"
        assert scenario.probability == 0.4
        assert scenario.impact_score == 7.5


class TestMoatAssessment:
    def test_moat_assessment(self):
        moat = MoatAssessment(
            moat_type="Network Effects",
            strength=8.0,
            difficulty_to_copy="HARD",
            time_to_copy_months=18,
            cost_to_copy_usd=5000000,
            explanation="Strong network effects from user base",
        )
        assert moat.strength == 8.0
        assert moat.difficulty_to_copy == "HARD"
        assert moat.time_to_copy_months == 18


class TestFinancialMetrics:
    def test_financial_metrics(self):
        metrics = FinancialMetrics(
            arr=1200000,
            mrr=100000,
            gross_margin_percent=72.5,
            cac=150,
            ltv=450,
            ltv_cac_ratio=3.0,
            burn_rate=50000,
            burn_multiple=1.5,
            payback_period_months=6,
            cash_runway_months=18,
            break_even_month=24,
            assumptions=["SaaS pricing model"],
        )
        assert metrics.arr == 1200000
        assert metrics.ltv_cac_ratio == 3.0
        assert metrics.break_even_month == 24


class TestInvestorRecommendation:
    def test_investor_recommendation(self):
        rec = InvestorRecommendation(
            recommendation="INVEST",
            investment_thesis="Strong team in growing market",
            reasons_to_invest=["Large TAM", "Strong team"],
            reasons_not_to_invest=["Unproven model"],
            fatal_risks=["Market timing"],
            biggest_unknowns=["Customer willingness to pay"],
            competitive_advantages=["First mover"],
            exit_opportunities=["Acquisition by Google"],
            expected_roi="3-5x over 5 years",
            confidence=ConfidenceScore(score=72.0),
            due_diligence_checklist=["Customer references", "Financial audit"],
        )
        assert rec.recommendation == "INVEST"
        assert rec.confidence.score == 72.0
        assert len(rec.reasons_to_invest) == 2
