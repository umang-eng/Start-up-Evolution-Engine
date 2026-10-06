from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient
from backend.models.blueprint import Blueprint
from backend.models.project import Project
from backend.models.workflow import GenerationSession, WorkflowEvent

from backend.schemas.user import UserCreate
from backend.services.user import user_service

pytestmark = pytest.mark.asyncio


async def test_compiled_blueprint_includes_latest_intelligence_stage_results(
    client: AsyncClient,
    db_session: Any,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(email="blueprint-stages@test.com", password="TestPassword123!"),
    )
    token = user_service.generate_user_tokens(user).access_token
    headers = {"Authorization": f"Bearer {token}"}
    project = Project(
        user_id=user.id,
        title="Persisted Intelligence",
        description="A test startup with persisted intelligence modules.",
        industry="SaaS",
    )
    db_session.add(project)
    await db_session.flush()

    blueprint = Blueprint(
        project_id=project.id,
        data={"executive_summary": {"business_summary": "Complete"}},
        health_score=75.0,
    )
    older_session = GenerationSession(
        project_id=project.id,
        status="COMPLETED",
        correlation_id=str(uuid.uuid4()),
        progress_percentage=100.0,
    )
    latest_session = GenerationSession(
        project_id=project.id,
        status="COMPLETED",
        correlation_id=str(uuid.uuid4()),
        progress_percentage=100.0,
    )
    db_session.add_all([blueprint, older_session, latest_session])
    await db_session.flush()

    now = datetime.now(timezone.utc)
    stages = (
        "competitive_moat",
        "stress_test",
        "financial_intelligence",
        "investment_committee",
        "product_execution",
        "global_expansion",
    )
    events = [
        WorkflowEvent(
            session_id=older_session.id,
            event_type="module:completed",
            stage="competitive_moat",
            payload={"result_version": "old", "_cache_status": "miss"},
            created_at=now,
        ),
        *[
            WorkflowEvent(
                session_id=latest_session.id,
                event_type="module:completed",
                stage=stage,
                payload={"result_version": "latest", "_cache_status": "miss"},
                created_at=now + timedelta(seconds=index + 1),
            )
            for index, stage in enumerate(stages)
        ],
    ]
    db_session.add_all(events)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/blueprints/{project.id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["executive_summary"]["business_summary"] == "Complete"
    assert set(stages).issubset(data)
    assert data["competitive_moat"]["result_version"] == "latest"
    assert "_cache_status" not in data["competitive_moat"]


async def test_project_crud_and_generator_api_flow(client: AsyncClient, db_session: Any) -> None:
    # 1. Register and login to generate token
    user_payload = UserCreate(email="builder@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Project
    project_payload = {
        "title": "Clean Tech Energy",
        "description": "Smart grids solutions",
        "industry": "GreenTech"
    }
    response = await client.post("/api/v1/projects", json=project_payload, headers=headers)
    assert response.status_code == 201
    proj_data = response.json()
    assert proj_data["success"] is True
    assert proj_data["data"]["title"] == "Clean Tech Energy"
    
    project_id = proj_data["data"]["id"]

    # 3. Read Project
    get_response = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["data"]["title"] == "Clean Tech Energy"

    # 4. List Projects
    list_response = await client.get("/api/v1/projects", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    # 5. Trigger Generator Run
    run_response = await client.post(f"/api/v1/generator/run?project_id={project_id}", headers=headers)
    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["success"] is True
    assert run_data["data"]["status"] == "QUEUED"
    assert "correlation_id" in run_data["data"]

    # 6. Fetch Blueprint (Not compiled yet, should return 404)
    blueprint_response = await client.get(f"/api/v1/blueprints/{project_id}", headers=headers)
    assert blueprint_response.status_code == 404
    assert blueprint_response.json()["success"] is False
    assert blueprint_response.json()["error"]["code"] == "BLUEPRINT_NOT_FOUND"

    # 7. Delete Project
    del_response = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_response.status_code == 200
    assert del_response.json()["success"] is True


async def test_enhance_idea_api(client: AsyncClient, db_session: Any) -> None:
    # 1. Register and login
    user_payload = UserCreate(email="enhancer@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Call Enhance API with valid data
    payload = {"idea": "Fitness coaching app for busy people"}
    response = await client.post("/api/v1/generator/enhance", json=payload, headers=headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    assert "enhanced_idea" in res_data["data"]
    assert res_data["data"]["original_idea"] == payload["idea"]


async def test_generator_run_specific_stage(client: AsyncClient, db_session: Any) -> None:
    # 1. Register and login
    user_payload = UserCreate(email="stage_runner@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Project
    project_payload = {
        "title": "Clean Energy Solutions",
        "description": "Solar panels microgrid",
        "industry": "CleanTech"
    }
    response = await client.post("/api/v1/projects", json=project_payload, headers=headers)
    assert response.status_code == 201
    project_id = response.json()["data"]["id"]

    # 3. Trigger Generator Run for 'dna' stage specifically
    run_response = await client.post(f"/api/v1/generator/run?project_id={project_id}&stage=dna", headers=headers)
    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["success"] is True
    assert run_data["data"]["status"] == "QUEUED"


async def test_generator_can_resume_from_the_first_incomplete_stage(
    client: AsyncClient,
    db_session: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = await user_service.register_user(
        db_session,
        obj_in=UserCreate(
            email="resume-generator@test.com",
            password="StrongPassword123!",
        ),
    )
    project = Project(
        user_id=user.id,
        title="Resume generation",
        description="A startup project to test resuming generation.",
        industry="SaaS",
    )
    db_session.add(project)
    await db_session.flush()
    headers = {
        "Authorization": f"Bearer {user_service.generate_user_tokens(user).access_token}"
    }
    enqueue = AsyncMock(return_value="resume-job")
    monkeypatch.setattr("backend.api.v1.generator.enqueue_compilation", enqueue)

    response = await client.post(
        f"/api/v1/generator/run?project_id={project.id}&start_from_stage=product_execution",
        headers=headers,
    )

    assert response.status_code == 200
    assert enqueue.await_args.kwargs["start_from_stage"] == "product_execution"
    assert enqueue.await_args.kwargs["target_stage"] is None
