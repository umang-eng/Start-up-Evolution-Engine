import logging
import asyncio
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.dependencies import get_token_payload, verify_project_access
from backend.database.session import get_db
from backend.models.blueprint import Blueprint
from backend.models.project import Project
from backend.exports.export import export_compiler
from backend.core.security import decode_token
from backend.core.config import settings

router = APIRouter(prefix="/exports", tags=["Document Exports"])

logger = logging.getLogger("app.exports")


async def prepare_blueprint_export_data(
    blueprint_data: dict[str, Any],
    project: Project,
    persisted_stages: dict[str, Any],
    intelligence_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Reconcile a stored blueprint with current stage records before document export."""
    from backend.modules.competitive_moat.module import CompetitiveMoatModule
    from backend.modules.cost.module import CostModule
    from backend.modules.financial_intelligence.module import FinancialIntelligenceModule
    from backend.modules.global_expansion.module import GlobalExpansionModule
    from backend.modules.investment_committee.module import InvestmentCommitteeModule
    from backend.modules.legal_compliance.module import LegalComplianceModule
    from backend.modules.product_execution.module import ProductExecutionModule
    from backend.modules.roadmap.module import RoadmapModule
    from backend.modules.swot.module import ensure_swot_sections

    data = dict(blueprint_data)
    data["_project_title"] = project.title
    for stage_name, record in persisted_stages.items():
        stage_data = getattr(record, "data", None) if record else None
        if isinstance(stage_data, dict) and stage_data:
            data[stage_name] = dict(stage_data)

    # Workflow events are the source of truth for generated intelligence stages.
    for stage_name, stage_data in intelligence_results.items():
        if isinstance(stage_data, dict) and stage_data:
            data[stage_name] = dict(stage_data)

    if isinstance(data.get("execution_roadmap"), dict):
        data["execution_roadmap"] = RoadmapModule.normalize_roadmap(data["execution_roadmap"])

    context = {
        "features": data.get("product_architecture", {}),
        "team": data.get("team_structure", {}),
        "roadmap": data.get("execution_roadmap", {}),
    }
    cost = data.get("financial_plan")
    if isinstance(cost, dict):
        data["financial_plan"] = CostModule._build_estimates(cost, context)
        context["cost"] = data["financial_plan"]

    if isinstance(data.get("swot_analysis"), dict):
        data["swot_analysis"] = ensure_swot_sections(
            data["swot_analysis"],
            project.description or project.title,
            project.industry or "the target industry",
        )

    product_execution = data.get("product_execution")
    if isinstance(product_execution, dict):
        product_text = " ".join(
            str(value) for value in (
                product_execution.get("prd_summary", ""),
                product_execution.get("product_vision", ""),
                (product_execution.get("technical_architecture") or {}).get("system_overview", ""),
                product_execution.get("explanation", ""),
            )
        ).casefold()
        if (
            not product_execution.get("user_stories")
            or len(product_execution.get("sprints") or []) < 6
            or any(marker in product_text for marker in (
                "requires detailed feature specifications",
                "architecture to be defined",
                "to be designed based on specific requirements",
            ))
        ):
            data["product_execution"] = ProductExecutionModule()._fallback_output([], {
                **context,
                "startup_idea": project.description or project.title,
                "product_description": project.description or project.title,
                "industry": project.industry or "technology",
            }).model_dump()

    financial_intelligence = data.get("financial_intelligence")
    if isinstance(financial_intelligence, dict):
        metrics = financial_intelligence.get("metrics") or {}
        assumptions = (
            financial_intelligence.get("key_assumptions") or []
        ) + (metrics.get("assumptions") or [])
        uncertainty_text = " ".join([
            str(financial_intelligence.get("explanation", "")),
            *(str(item) for item in assumptions),
        ]).casefold()
        if any(marker in uncertainty_text for marker in (
            "fallback", "requires actual financial data", "not validated", "unvalidated baseline",
        )):
            cost_data = data.get("financial_plan") or {}
            monthly_burn = float(cost_data.get("monthly_burn_usd", 0) or 0)
            if not monthly_burn:
                monthly_burn = sum(
                    float(item.get("monthly_usd", 0) or 0)
                    for item in cost_data.get("operational_costs", [])
                    if isinstance(item, dict)
                )
            data["financial_intelligence"] = FinancialIntelligenceModule()._fallback_output(
                [], monthly_burn
            ).model_dump()

    legal = data.get("legal_compliance")
    if isinstance(legal, dict):
        research_sources = str(legal.pop("_research_sources", ""))
        sanitized_legal = LegalComplianceModule.sanitize_output(
            legal,
            project.industry or "technology",
            getattr(project, "region", None) or "US",
            research_sources,
        )
        sanitized_legal.pop("_research_sources", None)
        data["legal_compliance"] = sanitized_legal

    moat = data.get("competitive_moat")
    if isinstance(moat, dict):
        dimensions = moat.get("moat_dimensions") or []
        if any(
            "fallback assessment" in str(item.get("explanation", "")).casefold()
            or "assessment unavailable" in str(item.get("explanation", "")).casefold()
            for item in dimensions if isinstance(item, dict)
        ):
            module = CompetitiveMoatModule()
            data["competitive_moat"] = (
                await module._generate_moat_output({}, module._fallback_dimensions([]), [])
            ).model_dump()

    expansion = data.get("global_expansion")
    if isinstance(expansion, dict):
        expansion_text = " ".join([
            str(expansion.get("explanation", "")),
            str(expansion.get("recommended_first_market", "")),
            str(expansion),
        ]).casefold()
        if any(marker in expansion_text for marker in (
            "fallback expansion", "local corp", "uk tech ltd", "canadian tech co",
        )):
            data["global_expansion"] = GlobalExpansionModule()._fallback_output([]).model_dump()

    committee = data.get("investment_committee")
    if isinstance(committee, dict):
        data["investment_committee"] = InvestmentCommitteeModule.sanitize_output(committee)

    risks = data.get("execution_risks")
    if not isinstance(risks, list) or not any(str(item).strip() for item in risks):
        data["execution_risks"] = [
            "Validate customer demand, access to representative industrial data, and delivery estimates before committing launch dates or investment."
        ]
    return data


@router.post("/pdf/{project_id}")
@router.get("/pdf/{project_id}")
async def export_pdf(
    project_id: str = Depends(verify_project_access),
    db: AsyncSession = Depends(get_db)
) -> Response:
    """Build a real PDF from the unified blueprint and persisted generated stage results."""
    import uuid
    project_uuid = uuid.UUID(project_id)
    
    # The compiled document can omit some stage results; merge their persisted outputs
    # so exports contain the same complete data the project workspace can display.
    stmt = select(Blueprint).where(Blueprint.project_id == project_uuid)
    result = await db.execute(stmt)
    blueprint = result.scalars().first()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unified blueprint has not been composed for this project yet."
        )

    project_stmt = (
        select(Project)
        .where(Project.id == project_uuid)
        .options(
            selectinload(Project.dna_result),
            selectinload(Project.feature_result),
            selectinload(Project.roadmap_result),
            selectinload(Project.team_result),
            selectinload(Project.swot_result),
            selectinload(Project.cost_result),
            selectinload(Project.legal_compliance_result),
        )
    )
    project = (await db.execute(project_stmt)).scalars().first()
    persisted_stages = {
        "startup_dna": project.dna_result if project else None,
        "product_architecture": project.feature_result if project else None,
        "execution_roadmap": project.roadmap_result if project else None,
        "team_structure": project.team_result if project else None,
        "swot_analysis": project.swot_result if project else None,
        "financial_plan": project.cost_result if project else None,
        "legal_compliance": project.legal_compliance_result if project else None,
    }

    from backend.api.v1.blueprints import _load_intelligence_results

    intelligence_results = await _load_intelligence_results(db, project_uuid)
    blueprint_data = await prepare_blueprint_export_data(
        dict(blueprint.data or {}),
        project,
        persisted_stages,
        intelligence_results,
    ) if project else dict(blueprint.data or {})

    try:
        pdf_bytes = await asyncio.to_thread(
            export_compiler.compile_blueprint_to_pdf,
            blueprint_data,
        )
    except Exception as exc:
        logger.exception("Failed to compile PDF for project %s", project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The blueprint PDF could not be generated. Check the server logs for details.",
        ) from exc

    headers = {
        "Content-Disposition": f"attachment; filename=\"blueprint-{project_id}.pdf\""
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/deck/{project_id}")
@router.get("/deck/{project_id}")
async def export_deck(
    project_id: str = Depends(verify_project_access),
    db: AsyncSession = Depends(get_db)
) -> Response:
    """Compiles the startup blueprint into a PowerPoint Pitch Deck presentation (.pptx)."""
    import uuid
    project_uuid = uuid.UUID(project_id)
    
    stmt = select(Blueprint).where(Blueprint.project_id == project_uuid)
    result = await db.execute(stmt)
    blueprint = result.scalars().first()

    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unified blueprint has not been composed for this project yet."
        )

    # Compile to PowerPoint (.pptx)
    deck_bytes = export_compiler.compile_blueprint_to_deck(blueprint.data)
    
    if deck_bytes:
        headers = {
            "Content-Disposition": f"attachment; filename=\"pitchdeck-{project_id}.pptx\""
        }
        return Response(
            content=deck_bytes, 
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", 
            headers=headers
        )
    
    # Fallback structure containing slides AST
    slides_ast = {
        "success": False,
        "message": "PowerPoint generation failed or library is not available. Here is the structured slide AST.",
        "slides": [
            {
                "title": blueprint.data.get("executive_summary", {}).get("startup_name", "Startup Pitch Deck"),
                "bullets": ["Strategic AI Platform Blueprint", "Generated by Start-up Evolution Engine"]
            }
        ]
    }
    
    if "dna" in blueprint.data:
        slides_ast["slides"].append({
            "title": "Value Proposition & DNA",
            "bullets": [
                f"USP: {blueprint.data['dna'].get('value_proposition', {}).get('core_usp')}",
                f"Revenue Model: {', '.join(blueprint.data['dna'].get('revenue_model', {}).get('revenue_streams', []))}"
            ]
        })
        
    return Response(
        content=str(slides_ast),
        media_type="application/json"
    )


@router.post("/share-link/{project_id}")
async def create_share_link(
    project_id: str = Depends(verify_project_access),
    scope: str = Query("investor:read", description="Access permission scope for the public link"),
    claims: dict[str, Any] = Depends(get_token_payload)
) -> dict[str, Any]:
    """Generates a tokenized public sharing URL with specific access scopes."""
    from jose import jwt as jose_jwt
    from datetime import datetime, timedelta, timezone

    # Generate a long-lived token (e.g., 30 days expiration) for the share scope
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    share_payload = {
        "sub": claims.get("sub"),
        "project_id": project_id,
        "scope": scope,
        "exp": expire,
        "type": "share"
    }
    
    token = jose_jwt.encode(share_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    share_url = f"/api/v1/blueprints/shared/{token}"
    
    return {
        "success": True,
        "data": {
            "share_token": token,
            "share_url": share_url,
            "scope": scope,
            "expires_at": expire.isoformat()
        },
        "metadata": {
            "api_version": "1.0.0"
        }
    }
