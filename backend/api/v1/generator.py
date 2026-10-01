"""
Generator API — Compilation Pipeline Trigger Endpoint

When a user hits POST /api/v1/generator/run, this module:
1. Validates tenancy and creates a GenerationSession with status PENDING
2. Enqueues the background task to the worker-engine via ARQ
3. Returns 202 Accepted with session_id so the frontend can subscribe to SSE
"""

import asyncio
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.api.dependencies import get_token_payload
from backend.api.arq_client import enqueue_compilation
from backend.core.config import settings
from backend.core.generation_lifecycle import (
    generation_session_is_stale,
    mark_generation_session_stale,
)
from backend.core.logging import logger
from backend.database.session import get_db
from backend.models.project import Project
from backend.models.workflow import GenerationSession
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.services.project import project_service

router = APIRouter(prefix="/generator", tags=["Generator Engine"])


# ── Response Schemas ───────────────────────────────────────────────

class RunAcceptedResponse(BaseModel):
    """Returned when a pipeline run is successfully enqueued."""
    project_id: str
    session_id: str
    correlation_id: str
    status: str = "PENDING"
    stream_url: str


class RunStatusResponse(BaseModel):
    """Current state of a project's latest generation session."""
    project_id: str
    session_id: str | None
    status: str
    current_stage: str | None
    progress_percentage: float
    error_message: str | None = None
    updated_at: str | None = None


# ── Endpoint ───────────────────────────────────────────────────────

@router.post(
    "/run",
    response_model=BaseResponse[RunAcceptedResponse],
    status_code=status.HTTP_200_OK,
)
async def trigger_run(
    project_id: uuid.UUID,
    stage: str | None = None,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload),
) -> dict[str, Any]:
    """Trigger the strategic compilation pipeline asynchronously.

    - Validates user tenancy on the project
    - Creates a GenerationSession record with status PENDING
    - Enqueues the job to the worker-engine via ARQ
    - Returns 202 Accepted with session_id and stream_url
    """
    user_id = uuid.UUID(claims["sub"])

    # Enforce tenancy verification
    project = await project_service.get_user_project(
        db, project_id=project_id, user_id=user_id
    )

    active_session = (
        await db.execute(
            select(GenerationSession)
            .where(
                GenerationSession.project_id == project.id,
                GenerationSession.status.in_(("PENDING", "INITIALIZING", "RUNNING")),
            )
            .order_by(GenerationSession.created_at.desc())
            .limit(1)
        )
    ).scalars().first()
    if active_session:
        if generation_session_is_stale(active_session):
            mark_generation_session_stale(active_session)
            await db.commit()
            logger.warning(
                "Marked stale generation session as failed; starting a fresh run",
                extra_data={
                    "project_id": str(project.id),
                    "session_id": str(active_session.id),
                    "stage": active_session.current_stage,
                },
            )
        else:
            return {
                "success": True,
                "data": RunAcceptedResponse(
                    project_id=str(project.id),
                    session_id=str(active_session.id),
                    correlation_id=active_session.correlation_id,
                    status=active_session.status,
                    stream_url=f"/api/v1/streams/{active_session.id}",
                ),
                "metadata": APIResponseMetadata(),
            }

    correlation_id = str(uuid.uuid4())

    # 1. Create GenerationSession with PENDING status
    session = GenerationSession(
        project_id=project.id,
        status="PENDING",
        correlation_id=correlation_id,
        current_stage="queued",
        progress_percentage=0.0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # 2. Enqueue the background task to worker-engine. In development, keep the
    # request usable when Redis/ARQ is not installed; Docker/production still
    # surfaces worker outages as 503.
    try:
        job_id = await enqueue_compilation(
            project_id=project.id,
            correlation_id=correlation_id,
            target_stage=stage,
        )
    except Exception as e:
        logger.error(f"Failed to enqueue compilation job: {e}", exc_info=e)
        if settings.ENVIRONMENT == "development":
            job_id = f"local:{session.id}"
            logger.warning("Running the compilation directly in the development API process because Redis/ARQ is unavailable.")
            from backend.worker.tasks import run_compilation_pipeline
            asyncio.create_task(
                run_compilation_pipeline(
                    {},
                    str(project.id),
                    correlation_id,
                    stage,
                )
            )
        else:
            session.status = "ENQUEUE_FAILED"
            session.error_message = str(e)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "success": False,
                    "error": {
                        "code": "WORKER_UNAVAILABLE",
                        "message": "Background worker is not available. Please try again.",
                    },
                },
            )

    # 3. Return 202 Accepted
    return {
        "success": True,
        "data": RunAcceptedResponse(
            project_id=str(project.id),
            session_id=str(session.id),
            correlation_id=correlation_id,
            status="QUEUED",
            stream_url=f"/api/v1/streams/{session.id}",
        ),
        "metadata": APIResponseMetadata(),
    }


@router.get(
    "/status/{project_id}",
    response_model=BaseResponse[RunStatusResponse],
)
async def get_run_status(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload),
) -> dict[str, Any]:
    """Return generation status and fail sessions that have exceeded their safe timeout."""
    user_id = uuid.UUID(claims["sub"])
    project = await project_service.get_user_project(
        db, project_id=project_id, user_id=user_id
    )
    session = (
        await db.execute(
            select(GenerationSession)
            .where(GenerationSession.project_id == project.id)
            .order_by(GenerationSession.created_at.desc())
            .limit(1)
        )
    ).scalars().first()

    if session and generation_session_is_stale(session):
        mark_generation_session_stale(session)
        await db.commit()
        await db.refresh(session)
        logger.warning(
            "Marked stale generation session as failed during status check",
            extra_data={
                "project_id": str(project.id),
                "session_id": str(session.id),
                "stage": session.current_stage,
            },
        )

    data = RunStatusResponse(
        project_id=str(project.id),
        session_id=str(session.id) if session else None,
        status=session.status if session else "IDLE",
        current_stage=session.current_stage if session else None,
        progress_percentage=float(session.progress_percentage) if session else 0.0,
        error_message=session.error_message if session else None,
        updated_at=session.updated_at.isoformat() if session else None,
    )
    return {
        "success": True,
        "data": data,
        "metadata": APIResponseMetadata(),
    }


@router.post("/cancel", response_model=BaseResponse[dict[str, str]])
async def cancel_run(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload),
) -> dict[str, Any]:
    """Request cancellation of the active pipeline for a project.

    The worker checks this durable status between stages. An in-flight Ollama
    request is allowed to finish, but no subsequent stage will be started.
    """
    user_id = uuid.UUID(claims["sub"])
    project = await project_service.get_user_project(db, project_id=project_id, user_id=user_id)
    session = (
        await db.execute(
            select(GenerationSession)
            .where(
                GenerationSession.project_id == project.id,
                GenerationSession.status.in_(("PENDING", "INITIALIZING", "RUNNING")),
            )
            .order_by(GenerationSession.created_at.desc())
        )
    ).scalars().first()

    if session:
        session.status = "CANCELLED"
        session.current_stage = None
        session.error_message = "Generation stopped by the user."
        await db.commit()

    return {
        "success": True,
        "data": {
            "project_id": str(project.id),
            "status": "CANCELLED" if session else "IDLE",
        },
        "metadata": APIResponseMetadata(),
    }


# ── Idea Enhancement (unchanged, runs synchronously on API gateway) ──

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
    claims: dict[str, Any] = Depends(get_token_payload),
) -> dict[str, Any]:
    """Uses Gemini AI to enhance and expand a startup idea description with strategic context."""
    from backend.ai.ollama import ollama_adapter

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
        enhanced_text = await ollama_adapter.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
        )
    except Exception as e:
        logger.error("Idea enhancement failed", exc_info=e)
        enhanced_text = (
            f"{payload.idea} — targeting early adopters via a SaaS subscription model "
            f"with freemium onboarding, monetized through usage-based pricing."
        )

    return {
        "success": True,
        "data": EnhanceIdeaResponse(
            enhanced_idea=enhanced_text,
            original_idea=payload.idea,
        ),
        "metadata": APIResponseMetadata(),
    }
