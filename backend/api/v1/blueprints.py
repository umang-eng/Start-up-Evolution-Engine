import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.core.exceptions import EntityNotFoundError
from backend.database.session import get_db
from backend.models.blueprint import Blueprint
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.services.project import project_service

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])


@router.get("/{project_id}", response_model=BaseResponse[dict[str, Any]])
async def get_compiled_blueprint(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Retrieve the fully compiled and resolved startup blueprint document."""
    user_id = uuid.UUID(claims["sub"])
    
    # 1. Verify project workspace tenancy
    await project_service.get_user_project(db, project_id=project_id, user_id=user_id)

    # 2. Fetch the compiled blueprint record
    stmt = select(Blueprint).where(Blueprint.project_id == project_id)
    result = await db.execute(stmt)
    blueprint = result.scalars().first()

    if not blueprint:
        raise EntityNotFoundError(
            message="No compiled blueprint exists for this project. Trigger generation first.",
            code="BLUEPRINT_NOT_FOUND"
        )

    return {
        "success": True,
        "data": blueprint.data,
        "metadata": APIResponseMetadata()
    }


@router.get("/shared/{token}", response_model=BaseResponse[dict[str, Any]])
async def get_shared_blueprint(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Retrieve a blueprint via a secure, tokenized public sharing URL (no standard login required)."""
    import jwt
    from backend.core.config import settings
    from backend.core.exceptions import BaseBusinessException

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as e:
        raise BaseBusinessException(
            message=f"The sharing link is invalid or has expired: {str(e)}",
            code="INVALID_SHARE_LINK",
            status_code=status.HTTP_401_UNAUTHORIZED if hasattr(status, "HTTP_401_UNAUTHORIZED") else 401
        )

    project_id_str = payload.get("project_id")
    if not project_id_str:
        raise BaseBusinessException(
            message="Invalid sharing link payload.",
            code="INVALID_SHARE_LINK",
            status_code=400
        )
        
    project_id = uuid.UUID(project_id_str)

    stmt = select(Blueprint).where(Blueprint.project_id == project_id)
    result = await db.execute(stmt)
    blueprint = result.scalars().first()

    if not blueprint:
        raise EntityNotFoundError(
            message="No compiled blueprint exists for this project.",
            code="BLUEPRINT_NOT_FOUND"
        )

    # Obfuscate sensitive salary data if scope is investor
    blueprint_data = blueprint.data.copy()
    scope = payload.get("scope", "investor:read")
    if scope == "investor:read":
        if "team" in blueprint_data and "roles" in blueprint_data["team"]:
            obfuscated_roles = []
            for role in blueprint_data["team"]["roles"]:
                obfuscated_role = role.copy()
                obfuscated_role["salary_range_usd_min"] = "CONFIDENTIAL"
                obfuscated_role["salary_range_usd_max"] = "CONFIDENTIAL"
                obfuscated_roles.append(obfuscated_role)
            blueprint_data["team"] = blueprint_data["team"].copy()
            blueprint_data["team"]["roles"] = obfuscated_roles

    return {
        "success": True,
        "data": blueprint_data,
        "metadata": APIResponseMetadata()
    }
