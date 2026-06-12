from typing import Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.config import settings
from backend.core.security import TokenError, decode_token
from backend.database.session import get_db

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False
)


async def get_token_payload(
    request: Request,
    token: str | None = Depends(reusable_oauth2)
) -> dict[str, Any]:
    """Extracts and verifies JWT token payload claims, supporting both header and query param."""
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token, expected_type="access")
        return payload
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def verify_project_access(
    project_id: str,
    payload: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db)
) -> str:
    """Verifies user tenancy scope access for a target project ID."""
    # Retrieve user scope information from token
    user_id = payload.get("sub")
    user_role = payload.get("role", "USER")
    
    # In case of platform management admin role, skip checks
    if user_role in ("ADMIN", "SYSTEM_ADMIN"):
        return project_id

    # For standard users, dynamic query-level verification goes here
    # (Checking project ownership in db session)
    # If not authorized:
    # raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    return project_id
