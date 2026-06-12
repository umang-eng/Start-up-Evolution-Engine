import pytest
import uuid
from typing import Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.user import UserCreate
from backend.services.user import user_service
from backend.models.project import Project
from backend.models.blueprint import Blueprint

pytestmark = pytest.mark.asyncio


async def test_exports_and_sharing_workflow(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Setup User and Project
    user_payload = UserCreate(email="exporter@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    project = Project(
        user_id=user.id,
        title="EcoDrive",
        description="Electric vehicle planning",
        industry="CleanTech"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # 2. Add Blueprint record for project
    blueprint_data = {
        "executive_summary": {
            "startup_name": "EcoDrive",
            "vision": "Green mobility for everyone",
            "summary": "Building electric vehicle route compilers."
        },
        "dna": {
            "value_proposition": {
                "core_usp": "Route compile optimization saving 15% battery life."
            },
            "revenue_model": {
                "revenue_streams": ["SaaS Subscription", "API Access"]
            }
        },
        "team": {
            "roles": [
                {
                    "role_title": "Lead Venture Architect",
                    "department": "Engineering",
                    "salary_range_usd_min": 120000,
                    "salary_range_usd_max": 150000,
                    "key_responsibilities": ["Lead development", "Architect systems"]
                }
            ]
        }
    }
    blueprint = Blueprint(
        project_id=project.id,
        data=blueprint_data,
        health_score=85.0
    )
    db_session.add(blueprint)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}

    # 3. Test PDF export (falls back to print-ready HTML if weasyprint not installed)
    response = await client.post(
        f"/api/v1/exports/pdf/{project.id}",
        headers=headers
    )
    assert response.status_code == 200
    assert "content-disposition" in response.headers
    assert "blueprint-" in response.headers["content-disposition"]

    # 4. Test Pitch Deck Slide export (falls back to structured JSON if python-pptx not installed)
    response_deck = await client.post(
        f"/api/v1/exports/deck/{project.id}",
        headers=headers
    )
    assert response_deck.status_code == 200
    assert "Content-Type" in response_deck.headers

    # 5. Test Share Link Generation
    response_share = await client.post(
        f"/api/v1/exports/share-link/{project.id}?scope=investor:read",
        headers=headers
    )
    assert response_share.status_code == 200
    share_payload = response_share.json()
    assert share_payload["success"] is True
    share_token = share_payload["data"]["share_token"]
    share_url = share_payload["data"]["share_url"]
    assert "shared" in share_url

    # 6. Test Shared Blueprint Retrieval & Obfuscation (public route, no login auth header)
    response_shared_blueprint = await client.get(
        share_url
    )
    assert response_shared_blueprint.status_code == 200
    shared_data = response_shared_blueprint.json()
    assert shared_data["success"] is True
    
    # Assert sensitive data is obfuscated as CONFIDENTIAL for investor:read scope
    roles = shared_data["data"]["team"]["roles"]
    assert roles[0]["salary_range_usd_min"] == "CONFIDENTIAL"
    assert roles[0]["salary_range_usd_max"] == "CONFIDENTIAL"
    assert roles[0]["role_title"] == "Lead Venture Architect"  # Non-sensitive field intact
