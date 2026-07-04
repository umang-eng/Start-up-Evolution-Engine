"""
Intake API — Dynamic Consultation Chat Endpoints.

Handles the 3-step intake flow:
1. POST /intake/start     → Analyze raw idea, return extraction + first question
2. POST /intake/message   → Submit answer, return next question
3. POST /intake/finalize  → Synthesize enriched package, create Project entity
"""

import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.core.logging import logger
from backend.database.session import get_db
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.schemas.intake import (
    IntakeStartRequest,
    IntakeStartResponse,
    IntakeMessageRequest,
    IntakeMessageResponse,
    IntakeFinalizeRequest,
    IntakeFinalizeResponse,
)
from backend.services.assistant import (
    start_intake_session,
    submit_answer,
    finalize_session,
)
from backend.services.project import project_service

router = APIRouter(prefix="/intake", tags=["Intake Consultation"])


@router.post(
    "/start",
    response_model=BaseResponse[IntakeStartResponse],
    status_code=status.HTTP_200_OK,
)
async def start_intake(
    payload: IntakeStartRequest,
    claims: dict[str, Any] = Depends(get_token_payload),
) -> dict[str, Any]:
    """Initiate an intake consultation session.

    Analyzes the raw startup idea using Gemini to extract:
    - Industry vertical
    - Target audience
    - Core value proposition
    - Sub-niche signals

    Then generates 3-4 hyper-targeted follow-up questions based on the
    detected industry. Returns the extraction metadata and the first question.
    """
    user_id = uuid.UUID(claims["sub"])
    logger.info(f"Intake started by user={user_id} idea={payload.raw_idea[:60]}...")

    result = await start_intake_session(raw_idea=payload.raw_idea)

    return {
        "success": True,
        "data": IntakeStartResponse(
            session_id=result["session_id"],
            extraction=result["extraction"],
            first_question=result["first_question"],
        ),
        "metadata": APIResponseMetadata(),
    }


@router.post(
    "/message",
    response_model=BaseResponse[IntakeMessageResponse],
    status_code=status.HTTP_200_OK,
)
async def send_message(
    payload: IntakeMessageRequest,
    claims: dict[str, Any] = Depends(get_token_payload),
) -> dict[str, Any]:
    """Submit an answer to a follow-up question and receive the next one.

    Validates the question_id matches the current pending question,
    stores the answer, and advances the conversation state.

    When all questions are answered, the response will have
    `is_complete: true` and the frontend should call `/intake/finalize`.
    """
    result = await submit_answer(
        session_id=payload.session_id,
        question_id=payload.question_id,
        answer=payload.answer,
    )

    return {
        "success": True,
        "data": IntakeMessageResponse(
            next_question=result["next_question"],
            questions_remaining=result["questions_remaining"],
            is_complete=result["is_complete"],
        ),
        "metadata": APIResponseMetadata(),
    }


@router.post(
    "/finalize",
    response_model=BaseResponse[IntakeFinalizeResponse],
    status_code=status.HTTP_200_OK,
)
async def finalize_intake(
    payload: IntakeFinalizeRequest,
    claims: dict[str, Any] = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Finalize the intake session and create the Project entity.

    Synthesizes all Q&A responses into a comprehensive enriched description
    using Gemini, then creates a Project entity with:
    - title: extracted from the raw idea (first ~80 chars)
    - description: the enriched multi-paragraph synthesis
    - industry: the confirmed/detected industry vertical

    Returns the intake package and the created project ID.
    """
    user_id = uuid.UUID(claims["sub"])

    # Finalize the intake session (triggers Gemini synthesis)
    package = await finalize_session(session_id=payload.session_id)

    # Create the Project entity from the intake package
    project_title = package.raw_idea[:80].strip()
    if len(package.raw_idea) > 80:
        # Try to cut at a word boundary
        last_space = project_title.rfind(" ")
        if last_space > 40:
            project_title = project_title[:last_space]

    try:
        project = await project_service.create_user_project(
            db,
            user_id=user_id,
            obj_in={
                "title": project_title,
                "description": package.enriched_description,
                "industry": package.industry,
            },
        )
        project_id = str(project.id)
        logger.info(f"Project created from intake | project={project_id} user={user_id}")
    except Exception as e:
        logger.error(f"Failed to create project from intake: {e}", exc_info=e)
        project_id = None

    return {
        "success": True,
        "data": IntakeFinalizeResponse(
            package=package,
            project_id=project_id,
        ),
        "metadata": APIResponseMetadata(),
    }
