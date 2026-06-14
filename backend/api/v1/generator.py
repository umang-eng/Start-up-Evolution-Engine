import uuid
from typing import Any
from fastapi import APIRouter, Depends, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.core.logging import logger
from backend.database.session import get_db, AsyncSessionLocal
from backend.models.project import Project
from backend.orchestrator.engine import orchestrator
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.services.project import project_service

router = APIRouter(prefix="/generator", tags=["Generator Engine"])


async def execute_background_compilation(project_id: uuid.UUID, correlation_id: str, stage: str | None = None) -> None:
    """Background task executor running orchestrator compilation using a fresh database session."""
    logger.info(f"Starting background pipeline run for project: {project_id}, stage: {stage}")
    async with AsyncSessionLocal() as db:
        try:
            project = await db.get(Project, project_id)
            if not project:
                logger.error(f"Project {project_id} not found for background execution!")
                return
            await orchestrator.execute_run(db, project, correlation_id, target_stage=stage)
        except Exception as e:
            logger.error(f"Background compilation runner crashed for project {project_id}", exc_info=e)


@router.post("/run", response_model=BaseResponse[dict[str, str]])
async def trigger_run(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Triggers the strategic compilation pipeline (full or specific stage) asynchronously."""
    user_id = uuid.UUID(claims["sub"])

    # Enforce tenancy verification
    project = await project_service.get_user_project(db, project_id=project_id, user_id=user_id)

    correlation_id = str(uuid.uuid4())

    # Enqueue the task asynchronously to avoid blocking the HTTP response
    background_tasks.add_task(execute_background_compilation, project.id, correlation_id, stage)

    return {
        "success": True,
        "data": {
            "project_id": str(project.id),
            "correlation_id": correlation_id,
            "status": "QUEUED"
        },
        "metadata": APIResponseMetadata()
    }


class EnhanceIdeaRequest(BaseModel):
    """Request payload for the AI idea enhancement endpoint."""
    idea: str = Field(min_length=10, max_length=2000, description="The startup idea text to enhance")


class EnhanceIdeaResponse(BaseModel):
    """Response from the AI idea enhancement endpoint."""
    enhanced_idea: str
    original_idea: str


@router.post("/enhance", response_model=BaseResponse[EnhanceIdeaResponse])
async def enhance_idea(
    payload: EnhanceIdeaRequest,
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Uses Gemini AI to enhance and expand a startup idea description with strategic context."""
    from backend.ai.gemini import gemini_adapter

    system_instruction = (
        "You are a world-class startup advisor and product strategist. "
        "When given a startup idea, expand and enhance it with specific details about "
        "the target market, monetization model, key differentiators, and strategic positioning. "
        "Keep the response concise (2-3 sentences maximum). Return only the enhanced idea text, no preamble."
    )

    prompt = (
        f"Enhance this startup idea with specific strategic details:\n\n"
        f"\"{payload.idea}\"\n\n"
        f"Return only the enhanced version of the idea, expanded with target market, "
        f"monetization model, and key differentiation. 2-3 sentences max."
    )

    try:
        enhanced_text = await gemini_adapter.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )
    except Exception as e:
        logger.error("Idea enhancement failed", exc_info=e)
        # Graceful degradation: return original with a standard enhancement
        enhanced_text = (
            f"{payload.idea} — targeting early adopters via a SaaS subscription model "
            f"with freemium onboarding, monetized through usage-based pricing."
        )

    return {
        "success": True,
        "data": EnhanceIdeaResponse(
            enhanced_idea=enhanced_text,
            original_idea=payload.idea
        ),
        "metadata": APIResponseMetadata()
    }
