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
from backend.modules.swot.module import build_swot_fallback
from backend.modules.swot.schemas import SWOTOutput


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
