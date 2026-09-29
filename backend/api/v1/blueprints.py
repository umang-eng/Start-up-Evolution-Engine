import uuid
from typing import Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload
from backend.core.exceptions import EntityNotFoundError
from backend.database.session import get_db
from backend.models.blueprint import Blueprint
from backend.models.workflow import GenerationSession, WorkflowEvent
from backend.schemas.base import BaseResponse, APIResponseMetadata
from backend.services.project import project_service

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])

INTELLIGENCE_STAGES = {
    "competitive_moat",
    "stress_test",
    "financial_intelligence",
    "investment_committee",
    "product_execution",
    "global_expansion",
}


async def _load_intelligence_results(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, dict[str, Any]]:
    """Load the latest persisted intelligence-stage output for each project stage."""
    event_stmt = (
        select(WorkflowEvent)
        .join(GenerationSession, WorkflowEvent.session_id == GenerationSession.id)
        .where(
            GenerationSession.project_id == project_id,
            WorkflowEvent.event_type == "module:completed",
            WorkflowEvent.stage.in_(INTELLIGENCE_STAGES),
        )
        .order_by(WorkflowEvent.created_at.desc())
    )
    events = (await db.execute(event_stmt)).scalars().all()
    results: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.stage and event.stage not in results:
            results[event.stage] = {
                key: value
                for key, value in (event.payload or {}).items()
                if not key.startswith("_")
            }
    return results


@router.get("/{project_id}", response_model=BaseResponse[dict[str, Any]])
async def get_compiled_blueprint(
    project_id: uuid.UUID,
    allow_partial: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Retrieve the fully compiled and resolved startup blueprint document."""
    user_id = uuid.UUID(claims["sub"])
    from backend.models.project import Project
    from sqlalchemy.orm import selectinload
    
    # 1. Verify project workspace tenancy and load related result stages
    stmt = select(Project).where(Project.id == project_id).options(
        selectinload(Project.blueprint),
        selectinload(Project.dna_result),
        selectinload(Project.feature_result),
        selectinload(Project.roadmap_result),
        selectinload(Project.team_result),
        selectinload(Project.swot_result),
        selectinload(Project.cost_result),
        selectinload(Project.legal_compliance_result),
    )
    result = await db.execute(stmt)
    project = result.scalars().first()
    if not project or project.user_id != user_id:
        raise EntityNotFoundError(
            message="Project workspace not found.",
            code="PROJECT_NOT_FOUND"
        )

    intelligence_results = await _load_intelligence_results(db, project_id)

    # Intelligence-stage outputs live in workflow events rather than the
    # core Blueprint schema, so merge them into both complete and partial views.
    if project.blueprint:
        blueprint_data = dict(project.blueprint.data or {})
        blueprint_data.update(intelligence_results)
        return {
            "success": True,
            "data": blueprint_data,
            "metadata": APIResponseMetadata()
        }

    if not allow_partial:
        raise EntityNotFoundError(
            message="No compiled blueprint exists for this project. Trigger generation first.",
            code="BLUEPRINT_NOT_FOUND"
        )

    # 3. Fallback to construct a partial blueprint from existing stage results
    partial_data = {
        "executive_summary": None,
        "startup_dna": project.dna_result.data if project.dna_result else None,
        "product_architecture": project.feature_result.data if project.feature_result else None,
        "execution_roadmap": project.roadmap_result.data if project.roadmap_result else None,
        "team_structure": project.team_result.data if project.team_result else None,
        "swot_analysis": project.swot_result.data if project.swot_result else None,
        "financial_plan": project.cost_result.data if project.cost_result else None,
        "legal_compliance": (
            project.legal_compliance_result.data
            if project.legal_compliance_result else None
        ),
        "health_indicators": None,
        "conflict_resolution_log": []
    }

    partial_data.update(intelligence_results)

    return {
        "success": True,
        "data": partial_data,
        "metadata": APIResponseMetadata()
    }


@router.get("/shared/{token}", response_model=BaseResponse[dict[str, Any]])
async def get_shared_blueprint(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Retrieve a blueprint via a secure, tokenized public sharing URL (no standard login required)."""
    from jose import jwt as jose_jwt, JWTError
    from backend.core.config import settings
    from backend.core.exceptions import BaseBusinessException

    try:
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as e:
        raise BaseBusinessException(
            message=f"The sharing link is invalid or has expired: {str(e)}",
            code="INVALID_SHARE_LINK",
            status_code=401
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
