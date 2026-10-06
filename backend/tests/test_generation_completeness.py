from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from pydantic import ValidationError

from backend.modules.cost.module import CostModule
from backend.modules.cost.schemas import CostOutput, FundingRequirement
from backend.modules.evidence.types import ConfidenceScore, FinancialMetrics
from backend.modules.blueprint.module import BlueprintModule
from backend.modules.financial_intelligence.schemas import (
    FinancialIntelligenceOutput,
    FinancialProjection,
    ScenarioFinancials,
    UnitEconomics,
)
from backend.modules.competitive_moat.module import CompetitiveMoatModule
from backend.modules.financial_intelligence.module import FinancialIntelligenceModule
from backend.modules.global_expansion.module import GlobalExpansionModule
from backend.modules.investment_committee.module import InvestmentCommitteeModule
from backend.modules.product_execution.module import ProductExecutionModule
from backend.modules.stress_test.module import StressTestModule
from backend.modules.stress_test.schemas import StressTestOutput
from backend.modules.swot.module import SWOTModule, build_swot_fallback
from backend.modules.swot.schemas import SWOTOutput
from backend.core.config import settings
from backend.core.exceptions import BaseBusinessException
from backend.core.generation_lifecycle import (
    generation_session_is_stale,
    generation_stale_after,
    mark_generation_session_stale,
)
from backend.ai.ollama import OllamaAdapter


def test_cost_output_normalizes_month_label_for_break_even() -> None:
    output = CostOutput(
        operational_costs=[],
        budget_scenarios=[],
        funding_requirements=FundingRequirement(
            minimum_target_usd=0,
            optimal_target_usd=0,
            runway_months=12,
            funding_suitability="",
        ),
        mvp_cost_estimate=1,
        year_1_cost_estimate=1,
        financial_risk_level="HIGH",
        break_even_month="Month 22",
    )

    assert output.break_even_month == 22


def test_cost_output_rejects_non_numeric_break_even_month() -> None:
    with pytest.raises(ValidationError):
        CostOutput(
            operational_costs=[],
            budget_scenarios=[],
            funding_requirements=FundingRequirement(
                minimum_target_usd=0,
                optimal_target_usd=0,
                runway_months=12,
                funding_suitability="",
            ),
            mvp_cost_estimate=1,
            year_1_cost_estimate=1,
            financial_risk_level="HIGH",
            break_even_month="When the company grows",
        )


def test_financial_intelligence_normalizes_model_month_labels_and_text_sections() -> None:
    metrics = FinancialMetrics(
        arr=0,
        mrr=0,
        gross_margin_percent=0,
        cac=0,
        ltv=0,
        ltv_cac_ratio=0,
        burn_rate=1000,
        burn_multiple=0,
        payback_period_months=0,
        cash_runway_months=0,
        break_even_month="Month 22",
    )
    scenario = ScenarioFinancials(
        scenario_name="Base case",
        probability=1,
        year1_revenue=0,
        year3_revenue=0,
        break_even_month="Month 22",
        total_funding_required=12000,
        runway_months=12,
        valuation_estimate=0,
    )

    output = FinancialIntelligenceOutput(
        metrics=metrics,
        unit_economics=UnitEconomics(
            cac=0,
            ltv=0,
            ltv_cac_ratio=0,
            payback_period_months=0,
            gross_margin_percent=0,
            net_margin_percent=0,
            contribution_margin_percent=0,
            churn_rate_percent=0,
            expansion_rate_percent=0,
        ),
        projections=[
            FinancialProjection(
                period="Month 1",
                revenue=0,
                costs=1000,
                profit=-1000,
                cash_balance=0,
                customers=0,
                arr=0,
                mrr=0,
            )
        ],
        scenarios=[scenario],
        funding_requirements="Seeking $1.5M-$2M seed funding for payroll and initial GTM.",
        valuation="Pre-money estimate $4M-$6M, subject to customer validation.",
        key_assumptions=[],
        financial_risks=[],
        recommendations=[],
        confidence=ConfidenceScore(score=20),
        explanation="Illustrative planning assumptions only.",
    )

    assert output.metrics.break_even_month == 22
    assert output.scenarios[0].break_even_month == 22
    assert output.funding_requirements["summary"].startswith("Seeking $1.5M")
    assert output.valuation["summary"].startswith("Pre-money estimate")


def test_financial_intelligence_estimates_unit_economics_from_customer_profile() -> None:
    economics, assumptions = FinancialIntelligenceModule._estimate_unit_economics({
        "dna": {"customer_type": "B2B", "business_model": "marketplace"},
        "industry": "industrial software",
    })

    assert economics.cac == 750
    assert economics.gross_margin_percent == 60
    assert economics.ltv == 10_000
    assert economics.ltv_cac_ratio == pytest.approx(13.33, rel=1e-3)
    assert economics.payback_period_months == 3
    assert any("illustrative planning estimates" in assumption.lower() for assumption in assumptions)


def test_financial_intelligence_completes_missing_metrics_without_overwriting_model_values() -> None:
    output = FinancialIntelligenceModule()._fallback_output([], 12_000)
    output.unit_economics.cac = 1_250
    output.metrics.cac = 1_250
    output.unit_economics.ltv = 0
    output.metrics.ltv = 0
    output.unit_economics.assumptions = []
    output.metrics.assumptions = []

    result = FinancialIntelligenceModule._complete_unit_economics(
        output,
        {"dna": {"customer_type": "B2C"}},
        12_000,
    )

    assert result.unit_economics.cac == result.metrics.cac == 1_250
    assert result.unit_economics.ltv == result.metrics.ltv > 0
    assert result.unit_economics.assumptions
    assert result.metrics.assumptions


def test_financial_metrics_normalizes_unspecified_break_even_to_unknown() -> None:
    metrics = FinancialMetrics(
        arr=0,
        mrr=0,
        gross_margin_percent=0,
        cac=0,
        ltv=0,
        ltv_cac_ratio=0,
        burn_rate=0,
        burn_multiple=0,
        payback_period_months=0,
        cash_runway_months=0,
        break_even_month="Not specified",
    )

    assert metrics.break_even_month is None


def test_blueprint_positioning_stays_complete_with_long_model_text() -> None:
    statement = BlueprintModule()._build_positioning_statement({
        "target_segments": ["manufacturing companies " * 20],
        "business_model": "subscription software " * 20,
        "category": "predictive maintenance " * 10,
        "value_proposition": "improve equipment uptime through data " * 20,
        "usp": "combine industrial data and machine learning " * 20,
    })

    assert len(statement) <= 500
    assert statement.endswith(".")
    assert not statement.endswith(("manufact", "predic", "improv", "machin"))


def test_stale_generation_is_failed_only_after_model_retry_window() -> None:
    now = datetime.now(timezone.utc)
    session = SimpleNamespace(
        status="RUNNING",
        current_stage="dna",
        created_at=now - generation_stale_after() - timedelta(seconds=1),
        updated_at=now - generation_stale_after() - timedelta(seconds=1),
        error_message=None,
    )

    assert generation_session_is_stale(session, now)
    message = mark_generation_session_stale(session)
    assert session.status == "FAILED"
    assert "during dna" in message
    assert "Retry generation" in message

    session.updated_at = now
    session.status = "RUNNING"
    assert not generation_session_is_stale(session, now)


def test_cost_estimates_are_derived_when_model_returns_zeroes() -> None:
    output = CostOutput(
        operational_costs=[],
        budget_scenarios=[],
        funding_requirements=FundingRequirement(
            minimum_target_usd=0,
            optimal_target_usd=0,
            runway_months=12,
            funding_suitability="",
        ),
        mvp_cost_estimate=0,
        year_1_cost_estimate=0,
        financial_risk_level="HIGH",
    )
    context = {
        "features": {
            "features": [
                {
                    "id": f"feature_{index}",
                    "name": f"Feature {index}",
                    "priority": "MUST_HAVE",
                    "category": "CORE",
                    "complexity": "MEDIUM",
                    "effort_estimate": "M",
                }
                for index in range(1, 4)
            ]
        },
        "team": {
            "org_chart": [
                {"title": "Software Engineer", "department": "Engineering", "estimated_salary_usd": 96_000}
            ]
        },
        "roadmap": {
            "phases": [
                {
                    "phase_id": "phase_mvp",
                    "name": "MVP",
                    "duration_months": 3,
                    "tasks": [],
                }
            ]
        },
    }

    result = CostModule._build_estimates(output, context)

    assert result["mvp_cost_estimate"] > 0
    assert result["year_1_cost_estimate"] > result["mvp_cost_estimate"]
    assert result["total_monthly_payroll_usd"] == 8_000
    assert len(result["feature_cost_breakdown"]) == 3
    assert len(result["budget_scenarios"]) == 3
    assert all(scenario["monthly_burn_usd"] > 0 for scenario in result["budget_scenarios"])


def test_product_execution_fallback_uses_features_and_produces_delivery_plan() -> None:
    context = {
        "startup_idea": "A scheduling platform for independent clinics",
        "industry": "healthcare software",
        "target_market": "independent clinics",
        "features": {
            "core_stack": ["FastAPI", "PostgreSQL"],
            "features": [
                {
                    "id": f"feature_{index}",
                    "name": f"Clinic workflow {index}",
                    "priority": "MUST_HAVE",
                    "effort_estimate": "M",
                }
                for index in range(1, 7)
            ],
        },
        "roadmap": {
            "total_estimated_weeks": 20,
            "phases": [
                {"name": "MVP delivery", "phase_objective": "Ship core clinic workflows"}
            ],
        },
        "team": {
            "org_chart": [{"title": "Product Engineer", "responsibilities": ["Build core workflows"]}]
        },
    }

    result = ProductExecutionModule()._fallback_output([], context)

    assert len(result.user_stories) >= 15
    assert len(result.sprints) == 6
    assert result.technical_architecture.components
    assert result.release_plan.features == [f"Clinic workflow {index}" for index in range(1, 7)]
    assert "requires detailed feature specifications" not in result.prd_summary


@pytest.mark.asyncio
async def test_product_execution_prompt_receives_pipeline_stage_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ProductExecutionModule()
    context = {
        "industry": "healthcare software",
        "product_description": "Clinic appointment scheduling",
        "target_market": "independent clinics",
        "features": {"features": [{"id": "booking", "name": "Appointment booking"}]},
        "roadmap": {"phases": [{"name": "MVP delivery", "duration_months": 3, "tasks": []}]},
        "team": {"org_chart": [{"title": "Product Engineer", "responsibilities": ["Build booking"]}]},
    }
    expected = module._fallback_output([], context)
    generator = AsyncMock(return_value=expected)
    monkeypatch.setattr("backend.modules.product_execution.module.ollama_adapter.generate", generator)

    result = await module._generate_execution(context, [])

    prompt = generator.call_args.kwargs["prompt"]
    assert "Appointment booking" in prompt
    assert "MVP delivery" in prompt
    assert "Product Engineer" in prompt
    assert result.sprints


@pytest.mark.asyncio
async def test_swot_fills_missing_opportunities_and_threats(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubDatabase:
        async def execute(self, _statement: object) -> SimpleNamespace:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None))

        def add(self, _record: object) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def refresh(self, _record: object) -> None:
            pass

    monkeypatch.setattr(
        SWOTModule,
        "_fetch_realtime_data",
        AsyncMock(return_value=("market data unavailable", "funding data unavailable")),
    )
    monkeypatch.setattr(
        "backend.modules.swot.module.ollama_adapter.generate",
        AsyncMock(return_value=SWOTOutput(
            strengths=[],
            weaknesses=[],
            opportunities=[],
            threats=[],
            mitigations=[],
            founder_actions=[],
        )),
    )
    project = SimpleNamespace(
        id=uuid.uuid4(),
        title="Clinic workflow",
        description="Scheduling for independent clinics",
        industry="healthcare software",
    )
    context = {
        "dna": {"category": "healthcare software"},
        "features": {"features": [{"name": "Scheduling"}]},
        "roadmap": {"phases": []},
        "team": {"org_chart": []},
    }

    output = await SWOTModule().run(StubDatabase(), project, context)  # type: ignore[arg-type]

    assert len(output["opportunities"]) >= 2
    assert len(output["threats"]) >= 2
    assert all("hypothesis" in entry.lower() or "risk" in entry.lower() for entry in output["opportunities"] + output["threats"])


@pytest.mark.asyncio
async def test_cost_generation_does_not_require_noncritical_swot(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubDatabase:
        async def execute(self, _statement: object) -> SimpleNamespace:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None))

        def add(self, _record: object) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def refresh(self, _record: object) -> None:
            pass

    output = CostOutput(
        operational_costs=[],
        budget_scenarios=[],
        funding_requirements=FundingRequirement(
            minimum_target_usd=0,
            optimal_target_usd=0,
            runway_months=12,
            funding_suitability="",
        ),
        mvp_cost_estimate=0,
        year_1_cost_estimate=0,
        financial_risk_level="HIGH",
    )
    monkeypatch.setattr(
        CostModule,
        "_fetch_realtime_data",
        AsyncMock(return_value=("cost data unavailable", "funding data unavailable")),
    )
    monkeypatch.setattr(
        "backend.modules.cost.module.ollama_adapter.generate",
        AsyncMock(return_value=output),
    )
    project = SimpleNamespace(
        id=uuid.uuid4(),
        title="Industrial maintenance platform",
        description="Predictive maintenance for manufacturers",
        industry="industrial software",
    )
    context = {
        "dna": {"category": "industrial software"},
        "features": {"features": [{"name": "Failure prediction", "priority": "MUST_HAVE"}]},
        "roadmap": {"phases": [{"name": "MVP", "duration_months": 3, "tasks": []}]},
        "team": {"org_chart": [{"title": "Engineer", "estimated_salary_usd": 120_000}]},
    }

    result = await CostModule().run(StubDatabase(), project, context)  # type: ignore[arg-type]

    assert result["total_monthly_payroll_usd"] == 10_000
    assert result["mvp_cost_estimate"] > 0


@pytest.mark.asyncio
async def test_cost_generation_uses_input_derived_baseline_for_invalid_model_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubDatabase:
        async def execute(self, _statement: object) -> SimpleNamespace:
            return SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None))

        def add(self, _record: object) -> None:
            pass

        async def commit(self) -> None:
            pass

        async def refresh(self, _record: object) -> None:
            pass

    monkeypatch.setattr(
        CostModule,
        "_fetch_realtime_data",
        AsyncMock(return_value=("cost data unavailable", "funding data unavailable")),
    )
    monkeypatch.setattr(
        "backend.modules.cost.module.ollama_adapter.generate",
        AsyncMock(side_effect=BaseBusinessException(
            "Expecting ',' delimiter: line 171 column 30",
            code="OLLAMA_VALIDATION_ERROR",
            status_code=422,
        )),
    )
    project = SimpleNamespace(
        id=uuid.uuid4(),
        title="Industrial maintenance platform",
        description="Predictive maintenance for manufacturers",
        industry="industrial software",
    )
    context = {
        "dna": {"category": "industrial software"},
        "features": {
            "features": [
                {"id": "prediction", "name": "Failure prediction", "priority": "MUST_HAVE"},
            ],
        },
        "roadmap": {"phases": [{"phase_id": "mvp", "name": "MVP", "duration_months": 3, "tasks": []}]},
        "team": {"org_chart": [{"title": "Engineer", "estimated_salary_usd": 120_000}]},
    }

    result = await CostModule().run(StubDatabase(), project, context)  # type: ignore[arg-type]
    validated = CostOutput.model_validate(result)

    assert validated.total_monthly_payroll_usd == 10_000
    assert validated.mvp_cost_estimate > 0
    assert len(validated.budget_scenarios) == 3
    assert "invalid JSON" in validated.key_cost_risks[0]
    assert "validate" in validated.funding_requirements.funding_suitability.lower()


def test_financial_fallback_does_not_invent_revenue_or_valuation() -> None:
    result = FinancialIntelligenceModule()._fallback_output([], 12_000)

    assert result.metrics.arr == result.metrics.mrr == 0
    assert result.projections[0].revenue == result.projections[0].arr == 0
    assert result.scenarios[0].year1_revenue == result.scenarios[0].year3_revenue == 0
    assert result.scenarios[0].valuation_estimate == result.valuation["estimated_value"] == 0
    assert result.projections[0].costs == 12_000
    assert result.scenarios[0].total_funding_required == 144_000
    assert "no revenue forecast" in result.explanation.lower()


def test_swot_fallback_is_complete_and_marks_unverified_claims_as_hypotheses() -> None:
    result = build_swot_fallback(
        "Predictive maintenance for industrial equipment",
        "industrial software",
        {"value_proposition": {"core_usp": "Reduce unplanned equipment downtime"}},
        {"features": [{"name": "Failure alerts"}]},
    )

    assert len(result.strengths) == 2
    assert len(result.weaknesses) == 2
    assert all(item.startswith("Hypothesis to validate:") for item in result.opportunities)
    assert all(item.startswith(("Risk to validate:", "Risk to monitor:")) for item in result.threats)
    assert len(result.mitigations) == len(result.threats)
    assert {action.horizon for action in result.founder_actions} == {
        "IMMEDIATE_30_DAYS",
        "SHORT_TERM_60_DAYS",
        "MEDIUM_TERM_90_DAYS",
        "LONG_TERM_BEYOND",
    }


@pytest.mark.asyncio
async def test_financial_intelligence_uses_safe_baseline_for_schema_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.modules.financial_intelligence.module.ollama_adapter.generate",
        AsyncMock(side_effect=BaseBusinessException(
            "Model output failed schema validation.",
            code="OLLAMA_VALIDATION_ERROR",
            status_code=422,
        )),
    )
    module = FinancialIntelligenceModule()

    result = await module._generate_financials(
        {
            "cost": {"monthly_burn_usd": 12_000},
            "dna": {"customer_type": "B2B", "business_model": "Subscription SaaS"},
            "industry": "industrial software",
        },
        [],
    )

    assert result.metrics.arr == result.metrics.mrr == 0
    assert result.metrics.cac > 0
    assert result.metrics.ltv > result.metrics.cac
    assert result.metrics.ltv_cac_ratio > 0
    assert result.unit_economics.payback_period_months > 0
    assert result.unit_economics.gross_margin_percent > 0
    assert result.unit_economics.contribution_margin_percent > 0
    assert result.unit_economics.churn_rate_percent > 0
    assert result.unit_economics.assumptions
    assert result.projections[0].revenue == 0
    assert result.projections[0].costs == 12_000
    assert result.scenarios[0].year1_revenue == 0
    assert result.scenarios[0].valuation_estimate == 0


def test_investment_committee_fallback_never_claims_a_real_offer() -> None:
    result = InvestmentCommitteeModule()._fallback_output([], 0)

    assert result.committee_members[0].firm == "Illustrative simulation — not an actual investor"
    assert result.term_sheet["investment_amount"] is None
    assert "no offer" in result.committee_members[0].suggested_terms.lower()


@pytest.mark.parametrize(
    ("model_category", "canonical_category"),
    [
        ("FINANCE", "ECONOMIC"),
        ("financial", "ECONOMIC"),
        ("competition", "COMPETITIVE"),
        ("tech", "TECHNOLOGICAL"),
        ("market", "MARKET"),
        ("customer", "MARKET"),
        ("management", "OPERATIONAL"),
    ],
)
def test_stress_test_normalizes_model_category_synonyms(
    model_category: str,
    canonical_category: str,
) -> None:
    model_output = StressTestModule()._fallback_output([]).model_dump()
    model_output["scenarios"][0]["category"] = model_category
    normalized = OllamaAdapter._sanitize_stress_test_data(model_output)
    validated = StressTestOutput.model_validate(normalized)

    assert validated.scenarios[0].category == canonical_category


@pytest.mark.asyncio
async def test_fast_mode_still_generates_intelligence_stages_with_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = SimpleNamespace(model_dump=lambda: {"generated_by_model": True})
    monkeypatch.setattr(settings, "PIPELINE_FAST_MODE", True)

    financial_generation = AsyncMock(return_value=generated)
    monkeypatch.setattr(FinancialIntelligenceModule, "_generate_financials", financial_generation)
    financial = await FinancialIntelligenceModule().run({"industry": "SaaS", "dna": {}}, [])

    stress_generation = AsyncMock(return_value=generated)
    monkeypatch.setattr(StressTestModule, "_generate_stress_test", stress_generation)
    stress = await StressTestModule().run({"industry": "SaaS"}, [])

    committee_generation = AsyncMock(return_value=generated)
    monkeypatch.setattr(InvestmentCommitteeModule, "_generate_ic", committee_generation)
    committee = await InvestmentCommitteeModule().run({"industry": "SaaS"}, [])

    expansion_generation = AsyncMock(return_value=generated)
    monkeypatch.setattr(GlobalExpansionModule, "_generate_expansion", expansion_generation)
    expansion = await GlobalExpansionModule().run({"industry": "SaaS"}, [])

    moat_assessment = AsyncMock(return_value=[])
    moat_generation = AsyncMock(return_value=generated)
    monkeypatch.setattr(CompetitiveMoatModule, "_assess_moat_dimensions", moat_assessment)
    monkeypatch.setattr(CompetitiveMoatModule, "_generate_moat_output", moat_generation)
    moat = await CompetitiveMoatModule().run(
        {"industry": "SaaS", "dna": {}, "features": {}}, []
    )

    assert all(
        result == {"generated_by_model": True}
        for result in (financial, stress, committee, expansion, moat)
    )
    assert all(
        generator.await_count == 1
        for generator in (
            financial_generation,
            stress_generation,
            committee_generation,
            expansion_generation,
            moat_assessment,
            moat_generation,
        )
    )


@pytest.mark.asyncio
async def test_product_execution_does_not_hide_cloud_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.modules.product_execution.module.ollama_adapter.generate",
        AsyncMock(side_effect=BaseBusinessException(
            "Ollama API key is required.",
            code="OLLAMA_AUTHENTICATION_REQUIRED",
            status_code=503,
        )),
    )

    with pytest.raises(BaseBusinessException, match="Ollama API key is required"):
        await ProductExecutionModule().run({"industry": "SaaS"}, [])
