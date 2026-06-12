import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.database.session import get_db
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.schemas.project import ProjectCreate, ProjectResponse
from backend.services.project import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=BaseResponse[ProjectResponse], status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Create a new startup project workspace."""
    user_id = uuid.UUID(claims["sub"])
    project = await project_service.create_user_project(db, user_id=user_id, obj_in=payload)
    return {
        "success": True,
        "data": ProjectResponse.model_validate(project),
        "metadata": APIResponseMetadata()
    }


@router.get("", response_model=BaseResponse[list[ProjectResponse]])
async def list_projects(
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """List all project workspaces belonging to the authenticated user."""
    user_id = uuid.UUID(claims["sub"])
    projects = await project_service.list_user_projects(db, user_id=user_id, offset=offset, limit=limit)
    return {
        "success": True,
        "data": [ProjectResponse.model_validate(p) for p in projects],
        "metadata": APIResponseMetadata()
    }


@router.get("/{project_id}", response_model=BaseResponse[ProjectResponse])
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Fetch metadata for a specific project workspace."""
    user_id = uuid.UUID(claims["sub"])
    project = await project_service.get_user_project(db, project_id=project_id, user_id=user_id)
    return {
        "success": True,
        "data": ProjectResponse.model_validate(project),
        "metadata": APIResponseMetadata()
    }


@router.delete("/{project_id}", response_model=BaseResponse[ProjectResponse])
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Delete a specific project workspace and clear cascading results."""
    user_id = uuid.UUID(claims["sub"])
    project = await project_service.delete_user_project(db, project_id=project_id, user_id=user_id)
    return {
        "success": True,
        "data": ProjectResponse.model_validate(project),
        "metadata": APIResponseMetadata()
    }
