from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from httpx import AsyncClient

from backend.core.generation_lifecycle import generation_stale_after
from backend.models.project import Project
from backend.models.workflow import GenerationSession
from backend.schemas.user import UserCreate
from backend.services.user import user_service

pytestmark = pytest.mark.asyncio


async def test_generation_status_marks_stale_runs_failed(
    client: AsyncClient,
    db_session: Any,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="generation-status@test.com", password="test-password-123"),
    )
    token = user_service.generate_user_tokens(user).access_token
    headers = {"Authorization": f"Bearer {token}"}
    project = Project(
        user_id=user.id,
        title="Generation status",
        description="A test project for generation liveness.",
        industry="SaaS",
    )
    db_session.add(project)
    await db_session.flush()

    stale_time = datetime.now(timezone.utc) - generation_stale_after() - timedelta(seconds=1)
    stale_session = GenerationSession(
        project_id=project.id,
        status="RUNNING",
        correlation_id="stale-status-check",
        current_stage="legal_compliance",
        progress_percentage=42.86,
        created_at=stale_time,
        updated_at=stale_time,
    )
    db_session.add(stale_session)
    await db_session.commit()

    stale_response = await client.get(
        f"/api/v1/generator/status/{project.id}",
        headers=headers,
    )
    assert stale_response.status_code == 200
    stale_data = stale_response.json()["data"]
    assert stale_data["status"] == "FAILED"
    assert stale_data["current_stage"] == "legal_compliance"
    assert "Retry generation" in stale_data["error_message"]

    active_session = GenerationSession(
        project_id=project.id,
        status="RUNNING",
        correlation_id="active-status-check",
        current_stage="financial_intelligence",
        progress_percentage=64.29,
    )
    db_session.add(active_session)
    await db_session.commit()

    active_response = await client.get(
        f"/api/v1/generator/status/{project.id}",
        headers=headers,
    )
    assert active_response.status_code == 200
    active_data = active_response.json()["data"]
    assert active_data["status"] == "RUNNING"
    assert active_data["current_stage"] == "financial_intelligence"
    assert active_data["progress_percentage"] == 64.29
