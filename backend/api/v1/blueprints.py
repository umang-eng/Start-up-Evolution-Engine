import uuid
from typing import Any
from fastapi import APIRouter, Depends
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
