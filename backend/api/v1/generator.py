import uuid
from typing import Any
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.core.config import settings
from backend.core.logging import logger
from backend.database.session import get_db, AsyncSessionLocal
from backend.models.project import Project
from backend.orchestrator.engine import orchestrator
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.services.project import project_service

router = APIRouter(prefix="/generator", tags=["Generator Engine"])


async def execute_background_compilation(project_id: uuid.UUID, correlation_id: str) -> None:
    """Background task executor running orchestrator compilation using a fresh database session."""
    logger.info(f"Starting background pipeline run for project: {project_id}")
    async with AsyncSessionLocal() as db:
        try:
            project = await db.get(Project, project_id)
            if not project:
                logger.error(f"Project {project_id} not found for background execution!")
                return
            await orchestrator.execute_run(db, project, correlation_id)
        except Exception as e:
            logger.error(f"Background compilation runner crashed for project {project_id}", exc_info=e)


@router.post("/run", response_model=BaseResponse[dict[str, str]])
async def trigger_run(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Triggers the full 7-stage strategic compilation pipeline asynchronously."""
    user_id = uuid.UUID(claims["sub"])
    
    # 1. Enforce tenancy verification
    project = await project_service.get_user_project(db, project_id=project_id, user_id=user_id)
    
    correlation_id = str(uuid.uuid4())

    # 2. Enqueue the task asynchronously to avoid blocking the HTTP response
    background_tasks.add_task(execute_background_compilation, project.id, correlation_id)

    return {
        "success": True,
        "data": {
            "project_id": str(project.id),
            "correlation_id": correlation_id,
            "status": "QUEUED"
        },
        "metadata": APIResponseMetadata()
    }
