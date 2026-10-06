import json
import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from backend.api.v1 import meetings as meetings_api
from backend.models.meeting import MeetingReport
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


async def test_reuploading_transcript_replaces_saved_text(
    client: AsyncClient,
    db_session: Any,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="meeting-transcript-reupload@test.com", password="Meeting-test-pass-123!"),
    )
    token = user_service.generate_user_tokens(user).access_token
    headers = {"Authorization": f"Bearer {token}"}

    meeting_response = await client.post(
        "/api/v1/meetings",
        json={"title": "Transcript replacement"},
        headers=headers,
    )
    meeting_id = meeting_response.json()["data"]["id"]

    first_upload = await client.post(
        f"/api/v1/meetings/{meeting_id}/transcript",
        json={"raw_text": "The original transcript.", "language_detected": "en"},
        headers=headers,
    )
    db_session.add(
        MeetingReport(
            meeting_id=uuid.UUID(meeting_id),
            status="COMPLETED",
            title="Report for original transcript",
        )
    )
    await db_session.commit()
    second_upload = await client.post(
        f"/api/v1/meetings/{meeting_id}/transcript",
        json={"raw_text": "The replacement transcript has four words.", "language_detected": "fr"},
        headers=headers,
    )

    assert first_upload.status_code == 200
    assert second_upload.status_code == 200
    assert second_upload.json()["data"]["id"] == first_upload.json()["data"]["id"]
    assert second_upload.json()["data"]["raw_text"] == "The replacement transcript has four words."
    assert second_upload.json()["data"]["word_count"] == 6
    assert second_upload.json()["data"]["language_detected"] == "fr"

    restored_transcript = await client.get(
        f"/api/v1/meetings/{meeting_id}/transcript",
        headers=headers,
    )
    assert restored_transcript.status_code == 200
    assert restored_transcript.json()["data"]["raw_text"] == "The replacement transcript has four words."
    stale_report = await client.get(
        f"/api/v1/meetings/{meeting_id}/report",
        headers=headers,
    )
    assert stale_report.status_code == 404


async def test_audio_upload_transcribes_and_saves_mp3(
    client: AsyncClient,
    db_session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="meeting-audio-upload@test.com", password="Meeting-test-pass-123!"),
    )
    token = user_service.generate_user_tokens(user).access_token
    headers = {"Authorization": f"Bearer {token}"}
    meeting_response = await client.post(
        "/api/v1/meetings",
        json={"title": "Audio upload"},
        headers=headers,
    )
    meeting_id = meeting_response.json()["data"]["id"]
    captured: dict[str, Any] = {}

    async def fake_transcribe_audio(*, audio_bytes: bytes, filename: str, language: str | None):
        captured.update(audio_bytes=audio_bytes, filename=filename, language=language)
        return {"text": "Transcript from uploaded audio.", "language": "en", "duration": 12.0}

    monkeypatch.setattr(meetings_api, "transcribe_audio", fake_transcribe_audio)
    response = await client.post(
        f"/api/v1/meetings/{meeting_id}/transcript/audio",
        headers=headers,
        files={"file": ("meeting.mp3", b"valid audio bytes" * 10, "audio/mpeg")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["raw_text"] == "Transcript from uploaded audio."
    assert captured == {
        "audio_bytes": b"valid audio bytes" * 10,
        "filename": "meeting.mp3",
        "language": None,
    }


async def test_audio_upload_rejects_files_over_size_limit(
    client: AsyncClient,
    db_session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="meeting-audio-limit@test.com", password="Meeting-test-pass-123!"),
    )
    token = user_service.generate_user_tokens(user).access_token
    headers = {"Authorization": f"Bearer {token}"}
    meeting_response = await client.post(
        "/api/v1/meetings",
        json={"title": "Oversized audio upload"},
        headers=headers,
    )
    meeting_id = meeting_response.json()["data"]["id"]
    monkeypatch.setattr(meetings_api, "MAX_AUDIO_UPLOAD_BYTES", 100)

    response = await client.post(
        f"/api/v1/meetings/{meeting_id}/transcript/audio",
        headers=headers,
        files={"file": ("meeting.mp3", b"x" * 101, "audio/mpeg")},
    )

    assert response.status_code == 413
    assert "100 MB or smaller" in response.json()["detail"]
