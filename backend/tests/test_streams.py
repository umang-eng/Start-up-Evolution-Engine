from typing import Any
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient

from backend.schemas.user import UserCreate
from backend.services.user import user_service

pytestmark = pytest.mark.asyncio


async def _stub_sse_generator(request: Any, project_id: str, max_duration: float = 300.0):
    """Test stub for sse_event_generator — yields the init handshake then terminates cleanly."""
    yield "event: system:init\ndata: {}\n\n"


async def test_progress_stream_handshake(client: AsyncClient, db_session: Any) -> None:
    """Verifies the SSE endpoint authenticates, returns 200 with correct content-type,
    and delivers the system:init handshake frame.

    The generator is stubbed to terminate after the init frame because the ASGI test
    transport does not support long-running async generators in-process.
    """
    user_payload = UserCreate(email="streamer@test.com", password="securepassword123")
    user = await user_service.register_user(db_session, obj_in=user_payload)
    tokens = user_service.generate_user_tokens(user)
    token = tokens.access_token

    project_id = str(uuid.uuid4())

    # Patch sse_event_generator with a deterministic stub that yields init and exits
    with patch("backend.api.v1.streams.sse_event_generator", new=_stub_sse_generator):
        # 1. Valid token → 200 SSE
        response = await client.get(
            f"/api/v1/streams/progress/{project_id}?token={token}",
            headers={"Accept": "text/event-stream"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "event: system:init" in response.text

        # 2. Missing token → 422 Unprocessable (missing required query param) OR 401 Unauthorized
        missing_token = await client.get(
            f"/api/v1/streams/progress/{project_id}",
            headers={"Accept": "text/event-stream"},
        )
        assert missing_token.status_code in (401, 422)

        # 3. Invalid/expired token → 401 Unauthorized
        bad_token = await client.get(
            f"/api/v1/streams/progress/{project_id}?token=not_a_real_jwt",
            headers={"Accept": "text/event-stream"},
        )
        assert bad_token.status_code == 401
