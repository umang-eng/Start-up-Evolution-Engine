from typing import Any
import uuid
import pytest
from httpx import AsyncClient

from backend.schemas.user import UserCreate
from backend.services.user import user_service

pytestmark = pytest.mark.asyncio


async def test_progress_stream_handshake(client: AsyncClient, db_session: Any) -> None:
    user_payload = UserCreate(email="streamer@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    project_id = str(uuid.uuid4())

    headers = {"Accept": "text/event-stream"}
    async with client.stream(
        "GET",
        f"/api/v1/streams/progress/{project_id}?token={token}",
        headers=headers
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        async for line in response.aiter_lines():
            if line:
                assert "event: system:init" in line or "data: {}" in line
                break

