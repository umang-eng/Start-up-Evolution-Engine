"""Tests for financial intelligence engine."""

import pytest
from backend.modules.financial_intelligence.schemas import (
    FinancialIntelligenceOutput, UnitEconomics, ScenarioFinancials, FinancialProjection
)
from backend.modules.evidence.types import ConfidenceScore, FinancialMetrics


class TestUnitEconomics:
    def test_create_unit_economics(self):
        ue = UnitEconomics(
            cac=150.0,
            ltv=450.0,
            ltv_cac_ratio=3.0,
            payback_period_months=6,
            gross_margin_percent=72.0,
            net_margin_percent=25.0,
            contribution_margin_percent=65.0,
            churn_rate_percent=5.0,
            expansion_rate_percent=12.0,
        )
        assert ue.cac == 150.0
        assert ue.ltv_cac_ratio == 3.0
        assert ue.churn_rate_percent == 5.0


class TestScenarioFinancials:
    def test_create_scenario(self):
        scenario = ScenarioFinancials(
            scenario_name="Base Case",
            probability=0.6,
            year1_revenue=120000,
            year3_revenue=600000,
            break_even_month=18,
            total_funding_required=300000,
            runway_months=18,
            valuation_estimate=2000000,
        )
        assert scenario.scenario_name == "Base Case"
        assert scenario.probability == 0.6
        assert scenario.valuation_estimate == 2000000


class TestFinancialProjection:
    def test_create_projection(self):
        proj = FinancialProjection(
            period="Month 6",
            revenue=50000,
            costs=30000,
            profit=20000,
            cash_balance=200000,
            customers=50,
            arr=600000,
            mrr=50000,
        )
        assert proj.period == "Month 6"
        assert proj.profit == 20000
        assert proj.arr == 600000


class TestFinancialIntelligenceOutput:
    def test_create_output(self):
        output = FinancialIntelligenceOutput(
            metrics=FinancialMetrics(
                arr=1200000, mrr=100000, gross_margin_percent=72.0,
                cac=150, ltv=450, ltv_cac_ratio=3.0,
                burn_rate=50000, burn_multiple=1.5,
                payback_period_months=6, cash_runway_months=18,
                assumptions=["SaaS model"],
            ),
            unit_economics=UnitEconomics(
                cac=150, ltv=450, ltv_cac_ratio=3.0,
                payback_period_months=6, gross_margin_percent=72.0,
                net_margin_percent=25.0, contribution_margin_percent=65.0,
                churn_rate_percent=5.0, expansion_rate_percent=12.0,
            ),
            projections=[
                FinancialProjection(
                    period="Month 1", revenue=0, costs=50000,
                    profit=-50000, cash_balance=250000,
                    customers=0, arr=0, mrr=0,
                )
            ],
            scenarios=[
                ScenarioFinancials(
                    scenario_name="Base", probability=0.6,
                    year1_revenue=120000, year3_revenue=600000,
                    break_even_month=18, total_funding_required=300000,
                    runway_months=18, valuation_estimate=2000000,
                )
            ],
            funding_requirements={"amount": 300000},
            valuation={"value": 2000000},
            key_assumptions=["SaaS pricing"],
            financial_risks=["Market uncertainty"],
            recommendations=["Focus on retention"],
            confidence=ConfidenceScore(score=65.0),
            explanation="Financial analysis complete",
        )
        assert output.metrics.arr == 1200000
        assert len(output.scenarios) == 1


class TestFinancialIntelligenceModule:
    @pytest.mark.asyncio
    async def test_module_initialization(self):
        from backend.modules.financial_intelligence.module import FinancialIntelligenceModule
        module = FinancialIntelligenceModule()
        assert module.stage_name == "financial_intelligence"
        assert "cost" in module.input_stages

    @pytest.mark.asyncio
    async def test_fallback_output(self):
        from backend.modules.financial_intelligence.module import FinancialIntelligenceModule
        module = FinancialIntelligenceModule()
        output = module._fallback_output([], 25000)
        assert isinstance(output, FinancialIntelligenceOutput)
        assert output.metrics.burn_rate == 25000
