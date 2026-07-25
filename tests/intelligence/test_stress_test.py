"""Tests for market stress testing module."""

import pytest
from backend.modules.stress_test.schemas import (
    StressTestOutput, StressTestScenario
)
from backend.modules.evidence.types import ConfidenceScore, EvidenceBackedScore


class TestStressTestScenario:
    def test_create_scenario(self):
        scenario = StressTestScenario(
            scenario_id="st-001",
            scenario_name="Competitor Entry",
            category="COMPETITIVE",
            description="Large competitor enters the market",
            trigger_event="Google launches competing product",
            impact="SEVERE",
            impact_score=7.5,
            probability=0.3,
            time_to_manifest_months=3,
            duration_months=12,
            affected_areas=["Revenue", "Market Share"],
            mitigation_strategy="Build switching costs",
            recovery_plan="Differentiate on niche features",
            recovery_time_months=6,
            expected_outcome="Reduced growth but survival",
            early_warning_signs=["Google hiring in our space"],
            pre_positioning=["Build community", "Lock in contracts"],
        )
        assert scenario.scenario_id == "st-001"
        assert scenario.impact == "SEVERE"
        assert scenario.probability == 0.3
        assert scenario.impact_score == 7.5

    def test_categories(self):
        valid_categories = ["COMPETITIVE", "MARKET", "REGULATORY", "TECHNOLOGICAL", "ECONOMIC", "OPERATIONAL"]
        for cat in valid_categories:
            scenario = StressTestScenario(
                scenario_id="test", scenario_name="Test", category=cat,
                description="Test", trigger_event="Test",
                impact="MINOR", impact_score=2.0, probability=0.1,
                time_to_manifest_months=1, duration_months=1,
                affected_areas=[], mitigation_strategy="Test",
                recovery_plan="Test", recovery_time_months=1,
                expected_outcome="Test",
            )
            assert scenario.category == cat


class TestStressTestOutput:
    def test_create_output(self):
        scenario = StressTestScenario(
            scenario_id="st-001", scenario_name="Downturn",
            category="ECONOMIC", description="Recession",
            trigger_event="Economic downturn", impact="SEVERE",
            impact_score=7.0, probability=0.3,
            time_to_manifest_months=6, duration_months=18,
            affected_areas=["Revenue"], mitigation_strategy="Cut costs",
            recovery_plan="Diversify", recovery_time_months=12,
            expected_outcome="Survival",
        )
        output = StressTestOutput(
            scenarios=[scenario],
            overall_resilience=EvidenceBackedScore(
                value=60.0, label="Resilience",
                confidence=ConfidenceScore(score=55.0),
            ),
            worst_case_scenario="Downturn",
            most_likely_scenario="Competitive Pressure",
            risk_score=EvidenceBackedScore(
                value=65.0, label="Risk",
                confidence=ConfidenceScore(score=50.0),
            ),
            resilience_recommendations=["Build reserves"],
            early_warning_system=["Monitor funding market"],
            explanation="Stress test complete",
        )
        assert len(output.scenarios) == 1
        assert output.overall_resilience.value == 60.0


class TestStressTestModule:
    @pytest.mark.asyncio
    async def test_module_initialization(self):
        from backend.modules.stress_test.module import StressTestModule
        module = StressTestModule()
        assert module.stage_name == "stress_test"
        assert "competitive_moat" in module.input_stages

    @pytest.mark.asyncio
    async def test_fallback_output(self):
        from backend.modules.stress_test.module import StressTestModule
        module = StressTestModule()
        output = module._fallback_output([])
        assert isinstance(output, StressTestOutput)
        assert len(output.scenarios) == 1
