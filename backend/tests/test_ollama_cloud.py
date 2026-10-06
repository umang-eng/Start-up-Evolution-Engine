import json
from types import SimpleNamespace

import pytest
import httpx
from pydantic import BaseModel

from backend.ai.ollama import OllamaAdapter, _raise_ollama_response_error
from backend.core.exceptions import BaseBusinessException
from backend.core.config import settings
from backend.modules.financial_intelligence.module import FinancialIntelligenceModule
from backend.modules.financial_intelligence.schemas import FinancialIntelligenceOutput
from backend.modules.investment_committee.module import InvestmentCommitteeModule
from backend.modules.investment_committee.schemas import InvestmentCommitteeOutput
from backend.modules.product_execution.module import ProductExecutionModule
from backend.modules.product_execution.schemas import ProductExecutionOutput
from backend.modules.stress_test.module import StressTestModule
from backend.modules.stress_test.schemas import StressTestOutput
from backend.modules.swot.module import build_swot_fallback
from backend.modules.swot.schemas import SWOTOutput
from backend.modules.blueprint.schemas import ExecutiveSummary


def test_cloud_credit_error_is_actionable() -> None:
    response = SimpleNamespace(status_code=402, text="account usage details")

    with pytest.raises(BaseBusinessException) as error:
        _raise_ollama_response_error(response, "glm-5.3-flash:cloud")

    assert error.value.status_code == 402
    assert error.value.code == "OLLAMA_CLOUD_CREDITS_REQUIRED"
    assert "https://ollama.com/settings" in error.value.message
    assert "paid usage" in error.value.message
    assert "account usage details" not in error.value.message


def test_cloud_authentication_error_does_not_echo_response_body() -> None:
    response = SimpleNamespace(status_code=401, text="sensitive response body")

    with pytest.raises(BaseBusinessException) as error:
        _raise_ollama_response_error(response, "glm-5.3-flash:cloud")

    assert error.value.status_code == 401
    assert error.value.code == "OLLAMA_AUTHENTICATION_REQUIRED"
    assert "ollama signin" in error.value.message
    assert "sensitive response body" not in error.value.message


@pytest.mark.asyncio
async def test_ollama_cloud_generates_schema_validated_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class ExampleOutput(BaseModel):
        answer: str

    captured: dict = {}
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "test-api-key")

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, url: str, *, json: dict, headers: dict):
            captured.update(url=url, payload=json, headers=headers)
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"message": {"content": '{"answer":"ready"}'}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    result = await OllamaAdapter().generate("Test prompt", ExampleOutput, "Test system")

    assert result.answer == "ready"
    assert captured["url"] == f"{settings.OLLAMA_HOST}/api/chat"
    assert captured["payload"]["model"] == settings.OLLAMA_MODEL
    assert captured["payload"]["format"] == "json"
    assert captured["payload"]["stream"] is False
    assert captured["headers"]["Authorization"] == "Bearer test-api-key"
    system_content = captured["payload"]["messages"][0]["content"]
    assert system_content.startswith("Test system\n\nIMPORTANT:")
    assert "Template structure:" in system_content


@pytest.mark.asyncio
async def test_stress_test_generation_uses_bounded_output_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    monkeypatch.setattr(settings, "OLLAMA_NUM_PREDICT", 4096)
    monkeypatch.setattr(settings, "OLLAMA_NUM_CTX", 8192)
    valid_output = StressTestModule()._fallback_output([]).model_dump(mode="json")
    valid_content = json.dumps(valid_output)

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, _url: str, *, json: dict, headers: dict):
            captured["payload"] = json
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": valid_content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    result = await OllamaAdapter().generate("Generate a stress test", StressTestOutput)

    assert result.scenarios
    assert captured["payload"]["options"]["num_predict"] == 4096
    assert captured["payload"]["options"]["num_ctx"] == 8192


@pytest.mark.asyncio
async def test_ollama_readiness_checks_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "test-api-key")

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, url: str, *, headers: dict):
            captured.update(url=url, headers=headers)
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"models": [{"name": settings.OLLAMA_MODEL}]},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    status = await OllamaAdapter().check_availability()

    assert status == {"model": settings.OLLAMA_MODEL, "host": settings.OLLAMA_HOST}
    assert captured["url"] == f"{settings.OLLAMA_HOST}/api/tags"
    assert captured["timeout"] == 5.0
    assert captured["headers"]["Authorization"] == "Bearer test-api-key"


@pytest.mark.asyncio
async def test_ollama_readiness_reports_missing_model(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, *_args, **_kwargs):
            return SimpleNamespace(status_code=200, json=lambda: {"models": []})

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    with pytest.raises(BaseBusinessException) as error:
        await OllamaAdapter().check_availability()

    assert error.value.code == "OLLAMA_MODEL_NOT_FOUND"
    assert "ollama pull" in error.value.message


@pytest.mark.asyncio
async def test_ollama_readiness_reports_connection_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, *_args, **_kwargs):
            raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    with pytest.raises(BaseBusinessException) as error:
        await OllamaAdapter().check_availability()

    assert error.value.code == "OLLAMA_UNAVAILABLE"
    assert "Start Ollama" in error.value.message
    assert settings.OLLAMA_MODEL in error.value.message


@pytest.mark.asyncio
async def test_financial_intelligence_discards_placeholder_evidence_and_unknown_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = FinancialIntelligenceModule()._fallback_output([], 12_000).model_dump(mode="json")
    payload["metrics"]["break_even_month"] = "Not specified"
    malformed_evidence = {
        "source_name": "Not specified",
        "source_url": "",
        "source_type": "Not specified",
        "retrieval_date": "Not specified",
        "snippet": "",
        "relevance_score": 0.8,
    }
    payload["metrics"]["evidence"] = [malformed_evidence]
    payload["unit_economics"]["evidence"] = [malformed_evidence]
    payload["scenarios"][0]["break_even_month"] = "Not specified"
    payload["scenarios"][0]["evidence"] = [malformed_evidence]
    payload["evidence"] = [malformed_evidence]
    payload["confidence"]["evidence"] = [malformed_evidence]

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(
                status_code=200,
                json=lambda: {"message": {"content": json.dumps(payload)}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    output = await OllamaAdapter().generate(
        "Generate financial analysis",
        FinancialIntelligenceOutput,
    )

    assert output.metrics.break_even_month is None
    assert output.scenarios[0].break_even_month is None
    assert output.metrics.evidence == []
    assert output.unit_economics.evidence == []
    assert output.scenarios[0].evidence == []
    assert output.evidence == []
    assert output.confidence.evidence == []


@pytest.mark.asyncio
async def test_investment_committee_normalizes_string_dictionary_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = InvestmentCommitteeModule()._fallback_output([], 12_000).model_dump(mode="json")
    payload["vote_tally"] = "INVEST"
    payload["term_sheet"] = "Term sheet to be developed after investment recommendation."
    payload["due_diligence_status"] = "PENDING"
    content = json.dumps(payload)

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, _url: str, **_kwargs):
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    output = await OllamaAdapter().generate(
        "Generate an investment committee assessment",
        InvestmentCommitteeOutput,
    )

    assert output.vote_tally == {"INVEST": 1, "PASS": 0, "CONDITIONAL": 0}
    assert output.term_sheet["status"].startswith("Term sheet")
    assert output.due_diligence_status == {"General diligence": "PENDING"}


@pytest.mark.asyncio
async def test_product_execution_normalizes_string_architecture_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = ProductExecutionModule()._fallback_output([], {}).model_dump(mode="json")
    payload["technical_architecture"]["components"] = ["User Interface", "AI Engine"]
    payload["technical_architecture"]["api_endpoints"] = ["/blueprint/generate"]
    payload["technical_architecture"]["database_schema"] = ["User", "Blueprint"]
    payload["release_plan"]["milestones"] = ["MVP launch", "Market validation report"]
    content = json.dumps(payload)

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    output = await OllamaAdapter().generate(
        "Generate a product execution plan",
        ProductExecutionOutput,
    )

    assert output.technical_architecture.components[:2] == [
        {"name": "User Interface"},
        {"name": "AI Engine"},
    ]
    assert output.technical_architecture.api_endpoints[0] == {"path": "/blueprint/generate"}
    assert output.technical_architecture.database_schema[:2] == [
        {"name": "User"},
        {"name": "Blueprint"},
    ]
    assert output.release_plan.milestones[:2] == [
        {"name": "MVP launch"},
        {"name": "Market validation report"},
    ]


@pytest.mark.asyncio
async def test_swot_generation_retries_token_repeat_with_bounded_sampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_payloads: list[dict] = []
    valid_output = build_swot_fallback(
        "Industrial predictive maintenance",
        "industrial software",
        {},
        {},
    ).model_dump()
    valid_content = json.dumps(valid_output)

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, _url: str, *, json: dict, headers: dict):
            captured_payloads.append(json)
            if len(captured_payloads) == 1:
                return SimpleNamespace(
                    status_code=500,
                    text='{"error":"prediction aborted, token repeat limit reached"}',
                )
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": valid_content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    result = await OllamaAdapter().generate(
        "Generate a SWOT analysis",
        SWOTOutput,
    )

    assert len(captured_payloads) == 2
    assert captured_payloads[0]["options"]["num_predict"] == 2048
    assert captured_payloads[1]["options"]["num_predict"] == 1024
    assert captured_payloads[1]["options"]["repeat_penalty"] == 1.2
    assert result.opportunities
    assert result.threats


@pytest.mark.asyncio
async def test_blueprint_summary_retries_token_repeat_with_bounded_sampling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_payloads: list[dict] = []
    valid_content = json.dumps({
        "business_summary": "A focused plan for the stated target customer.",
        "strategic_summary": "Differentiate through the supplied product capabilities.",
        "execution_summary": "Validate demand, then deliver a scoped MVP.",
        "financial_summary": "Costs and funding need validation before forecasting.",
        "founder_directives": ["Interview target customers", "Validate willingness to pay"],
    })

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, _url: str, *, json: dict, headers: dict):
            captured_payloads.append(json)
            if len(captured_payloads) == 1:
                return SimpleNamespace(
                    status_code=500,
                    text='{"error":"prediction aborted, token repeat limit reached"}',
                )
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": valid_content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    result = await OllamaAdapter().generate(
        "Synthesize the final startup blueprint",
        ExecutiveSummary,
    )

    assert len(captured_payloads) == 2
    assert captured_payloads[0]["options"]["num_predict"] >= 4096
    assert captured_payloads[1]["options"]["num_predict"] == 2048
    assert captured_payloads[1]["options"]["repeat_penalty"] == 1.2
    assert result.business_summary.startswith("A focused plan")


@pytest.mark.asyncio
async def test_blueprint_summary_converts_list_and_dict_narratives_to_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = json.dumps({
        "business_summary": ["Blueprint AI offers a focused solution.", "It targets early adopters."],
        "strategic_summary": ["Differentiate through workflow automation.", "Validate market demand."],
        "execution_summary": ["Build the MVP.", "Test with target users."],
        "financial_summary": {
            "operational_costs": [{"category": "compute", "monthly": "$63"}],
            "funding_basis": "Validate actual cash needs.",
        },
        "founder_directives": ["Interview customers"],
    })

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, *_args, **_kwargs):
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    output = await OllamaAdapter().generate(
        "Synthesize the final startup blueprint",
        ExecutiveSummary,
    )

    assert output.business_summary == (
        "Blueprint AI offers a focused solution.\nIt targets early adopters."
    )
    assert "Differentiate through workflow automation." in output.strategic_summary
    assert "Build the MVP." in output.execution_summary
    assert "operational costs:" in output.financial_summary
    assert "$63" in output.financial_summary
    assert "funding basis: Validate actual cash needs." in output.financial_summary


@pytest.mark.asyncio
async def test_swot_object_threats_are_normalized_to_schema_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = build_swot_fallback(
        "Industrial predictive maintenance",
        "industrial software",
        {},
        {},
    ).model_dump()
    payload["threats"] = [
        {
            "impact": 2,
            "probability": 2,
            "threat_description": "Industrial expertise in the field is limited.",
            "mitigation_strategy": "Partner with domain experts.",
        },
        {
            "impact": 3,
            "probability": 2,
            "description": "Competitors may enter similar markets.",
        },
    ]
    content = json.dumps(payload)

    class MockAsyncClient:
        def __init__(self, *, timeout: float) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, _url: str, **_kwargs):
            return SimpleNamespace(
                status_code=200,
                text="",
                json=lambda: {"message": {"content": content}},
            )

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    result = await OllamaAdapter().generate("Generate SWOT", SWOTOutput)

    assert result.threats == [
        "Industrial expertise in the field is limited.",
        "Competitors may enter similar markets.",
    ]
