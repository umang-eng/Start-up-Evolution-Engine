from typing import Any
import pytest
from httpx import AsyncClient

from backend.schemas.user import UserCreate
from backend.services.user import user_service

pytestmark = pytest.mark.asyncio


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



