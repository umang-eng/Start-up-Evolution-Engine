import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from backend.schemas.user import UserCreate
from backend.services.user import user_service
from backend.ai.ollama import ollama_adapter

pytestmark = pytest.mark.asyncio


async def test_meeting_health_and_combined_analysis_survive_reload(
    client: AsyncClient,
    db_session,
    monkeypatch,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="meeting-analysis@test.com", password="test-password-123"),
    )
    token = user_service.generate_user_tokens(user).access_token
    headers = {"Authorization": f"Bearer {token}"}

    meeting_response = await client.post(
        "/api/v1/meetings",
        json={"title": "Product planning"},
        headers=headers,
    )
    assert meeting_response.status_code == 201
    meeting_id = meeting_response.json()["data"]["id"]

    transcript_response = await client.post(
        f"/api/v1/meetings/{meeting_id}/transcript",
        json={"raw_text": "Speaker A: We agreed to prioritize the onboarding work."},
        headers=headers,
    )
    assert transcript_response.status_code == 200

    health_response = await client.post(
        f"/api/v1/meetings/{meeting_id}/health",
        headers=headers,
    )
    assert health_response.status_code == 200
    health = health_response.json()["data"]

    restored_health = await client.get(
        f"/api/v1/meetings/{meeting_id}/health",
        headers=headers,
    )
    assert restored_health.status_code == 200
    assert restored_health.json()["data"] == health

    combined_response = await client.post(
        f"/api/v1/meetings/{meeting_id}/analyze",
        headers=headers,
    )
    assert combined_response.status_code == 200
    combined = combined_response.json()["data"]

    restored_combined = await client.get(
        f"/api/v1/meetings/{meeting_id}/analysis",
        headers=headers,
    )
    assert restored_combined.status_code == 200
    assert restored_combined.json()["data"] == combined

    report_response = await client.get(
        f"/api/v1/meetings/{meeting_id}/report",
        headers=headers,
    )
    assert report_response.status_code == 404

    monkeypatch.setattr(
        ollama_adapter,
        "generate_text",
        AsyncMock(return_value=json.dumps({
            "title": "Product planning",
            "executive_summary": "The team prioritized onboarding.",
            "key_points": [],
            "decisions": [],
            "action_items": [],
            "questions_raised": [],
            "risks_concerns": [],
            "agreements": [],
            "disagreements": [],
            "technical_topics": [],
            "business_opportunities": [],
            "follow_up_needed": [],
            "overall_outcome": "Onboarding was prioritized.",
        })),
    )
    generated_report = await client.post(
        f"/api/v1/meetings/{meeting_id}/report/generate",
        headers=headers,
    )
    assert generated_report.status_code == 200

    restored_health = await client.get(
        f"/api/v1/meetings/{meeting_id}/health",
        headers=headers,
    )
    restored_combined = await client.get(
        f"/api/v1/meetings/{meeting_id}/analysis",
        headers=headers,
    )
    assert restored_health.json()["data"] == health
    assert restored_combined.json()["data"] == combined
