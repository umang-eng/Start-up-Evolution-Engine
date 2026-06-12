import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_auth_workflow_registration_and_login(client: AsyncClient) -> None:
    # 1. Register new user
    register_payload = {
        "email": "founder@test.com",
        "password": "securepassword123"
    }
    response = await client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    reg_data = response.json()
    assert reg_data["success"] is True
    assert reg_data["data"]["email"] == "founder@test.com"
    assert "id" in reg_data["data"]

    # 2. Try to register with duplicate email
    duplicate_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert duplicate_response.status_code == 409
    dup_data = duplicate_response.json()
    assert dup_data["success"] is False
    assert dup_data["error"]["code"] == "CONFLICT_DETECTED"

    # 3. Login with credentials
    login_payload = {
        "email": "founder@test.com",
        "password": "securepassword123"
    }
    login_response = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["success"] is True
    assert "access_token" in login_data["data"]
    assert "refresh_token" in login_data["data"]

    access_token = login_data["data"]["access_token"]
    refresh_token = login_data["data"]["refresh_token"]

    # 4. Fetch my profile using auth headers
    headers = {"Authorization": f"Bearer {access_token}"}
    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["success"] is True
    assert me_data["data"]["email"] == "founder@test.com"

    # 5. Refresh user session
    refresh_response = await client.post(
        f"/api/v1/auth/refresh?refresh_token={refresh_token}"
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["success"] is True
    assert "access_token" in refresh_data["data"]
    assert "refresh_token" in refresh_data["data"]
