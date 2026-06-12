import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_liveness_endpoint(client: AsyncClient) -> None:
    """Verify container liveness checks respond with success status."""
    response = await client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "healthy"
    assert "timestamp" in payload["metadata"]


async def test_readiness_endpoint(client: AsyncClient) -> None:
    """Verify backend system readiness checks check Postgres and Redis status."""
    response = await client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ready"
    assert payload["data"]["components"]["database"] == "UP"
    assert payload["data"]["components"]["redis"] == "UP"
