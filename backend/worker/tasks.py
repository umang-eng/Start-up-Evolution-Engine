"""
ARQ Worker Tasks — Background Pipeline Execution

This module defines the task functions that the ARQ worker picks up from the Redis queue.
Each task is a standalone async function that creates its own database session and runs
the orchestrator pipeline stage-by-stage, publishing progress events to Redis Pub/Sub.
"""

import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from backend.core.logging import logger
from backend.database.session import AsyncSessionLocal
from backend.models.project import Project
from backend.models.workflow import GenerationSession
from backend.cache.redis import redis_manager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Lazy-loaded orchestrator (avoids import-time side effects) ─────
_orchestrator = None
_local_pipeline_tasks: set[asyncio.Task[Any]] = set()


def schedule_local_pipeline(
    project_id: str,
    correlation_id: str,
    target_stage: str | None = None,
    start_from_stage: str | None = None,
) -> asyncio.Task[Any]:
    """Keep development fallback tasks referenced while they run."""
    task = asyncio.create_task(
        run_compilation_pipeline(
            {}, project_id, correlation_id, target_stage, start_from_stage
        )
    )
    _local_pipeline_tasks.add(task)
    task.add_done_callback(_local_pipeline_tasks.discard)
    return task


async def recover_local_pipeline_sessions(
    db: AsyncSession,
) -> list[tuple[str, str, str | None, str | None]]:
    """Requeue one interrupted local run after an API reload; fail repeated interruptions."""
    stmt = (
        select(GenerationSession)
        .where(GenerationSession.status.in_({"PENDING", "INITIALIZING", "RUNNING"}))
        .order_by(GenerationSession.created_at.asc())
    )
    sessions = (await db.execute(stmt)).scalars().all()
    jobs: list[tuple[str, str, str | None, str | None]] = []

    for session in sessions:
        cache_map = session.stage_cache_map or {}
        local_execution = cache_map.get("_local_execution")
        if not isinstance(local_execution, dict):
            continue

        recovery_attempts = int(local_execution.get("recovery_attempts", 0))
        if recovery_attempts >= 1:
            session.status = "FAILED"
            session.error_message = (
                "The development API restarted repeatedly during generation. "
                "Retry the run; completed stages will be reused where possible."
            )
            continue

        local_execution = {
            **local_execution,
            "recovery_attempts": recovery_attempts + 1,
        }
        session.stage_cache_map = {
            **cache_map,
            "_local_execution": local_execution,
        }
        session.status = "PENDING"
        session.current_stage = "queued"
        session.error_message = None
        jobs.append((
            str(session.project_id),
            session.correlation_id,
            local_execution.get("target_stage"),
            local_execution.get("start_from_stage"),
        ))

    if sessions:
        await db.commit()
    return jobs


def _get_orchestrator():
    """Lazily import and cache the orchestrator singleton with registered modules.

    Routes to AgentModule when agent mesh is enabled for a stage,
    otherwise uses the original BaseModule implementation.
    """
    global _orchestrator
    if _orchestrator is None:
        from backend.orchestrator.engine import WorkflowOrchestrator
        from backend.agents.config import AGENT_MESH_CONFIG

        _orchestrator = WorkflowOrchestrator()

        # Original module classes (fallback)
        from backend.modules.dna.module import DNAModule
        from backend.modules.features.module import FeatureModule
        from backend.modules.roadmap.module import RoadmapModule
        from backend.modules.team.module import TeamModule
        from backend.modules.swot.module import SWOTModule
        from backend.modules.cost.module import CostModule
        from backend.modules.blueprint.module import BlueprintModule
        from backend.modules.legal_compliance.module import LegalComplianceModule
        from backend.modules.competitive_moat.module import CompetitiveMoatModule
        from backend.modules.stress_test.module import StressTestModule
        from backend.modules.financial_intelligence.module import FinancialIntelligenceModule
        from backend.modules.investment_committee.module import InvestmentCommitteeModule
        from backend.modules.product_execution.module import ProductExecutionModule
        from backend.modules.global_expansion.module import GlobalExpansionModule

        stage_module_map: dict[str, type] = {
            "dna": DNAModule,
            "features": FeatureModule,
            "roadmap": RoadmapModule,
            "team": TeamModule,
            "swot": SWOTModule,
            "cost": CostModule,
            "blueprint": BlueprintModule,
            "legal_compliance": LegalComplianceModule,
            "competitive_moat": CompetitiveMoatModule,
            "stress_test": StressTestModule,
            "financial_intelligence": FinancialIntelligenceModule,
            "investment_committee": InvestmentCommitteeModule,
            "product_execution": ProductExecutionModule,
            "global_expansion": GlobalExpansionModule,
        }

        for stage_name, original_cls in stage_module_map.items():
            mesh_cfg = AGENT_MESH_CONFIG.get(stage_name)
            if mesh_cfg and mesh_cfg.enabled:
                from backend.agents.module import AgentModule
                _orchestrator.register_module(stage_name, AgentModule(stage_name))
                logger.info(
                    f"[Worker] Registered AgentModule for stage={stage_name}"
                )
            else:
                _orchestrator.register_module(stage_name, original_cls())

    return _orchestrator


async def _publish_event(channel: str, event_data: dict[str, Any]) -> None:
    """Publish a JSON event to a Redis Pub/Sub channel."""
    try:
        if not redis_manager.client:
            redis_manager.initialize()

        payload = event_data.copy()
        if not payload.get("timestamp"):
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()

        await redis_manager.publish(channel, json.dumps(payload))
    except Exception as e:
        logger.error(f"Worker failed to publish event to {channel}", exc_info=e)


async def run_compilation_pipeline(
    ctx: dict[str, Any],
    project_id: str,
    correlation_id: str,
    target_stage: str | None = None,
    start_from_stage: str | None = None,
) -> dict[str, Any]:
    """
    ARQ task: Execute the full 7-stage compilation pipeline for a project.

    This function runs inside the worker-engine process. It:
    1. Opens a fresh database session
    2. Loads the project
    3. Delegates to the orchestrator which publishes stage events to Redis Pub/Sub
    4. Returns a summary dict (ARQ serializes this back to Redis)

    Parameters:
        ctx: ARQ job context (contains job_id, etc.)
        project_id: UUID string of the target project
        correlation_id: Unique correlation ID for tracing
        target_stage: Optional single stage name to run (e.g. "dna")
        start_from_stage: Optional stage from which to resume the remaining pipeline
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    job_id = ctx.get("job_id", "unknown")
    stage_description = (
        target_stage
        or (f"from {start_from_stage}" if start_from_stage else "all")
    )
    logger.info(
        f"[Worker] Starting compilation pipeline | job={job_id} "
        f"project={project_id} stage={stage_description}"
    )

    async with AsyncSessionLocal() as db:
        try:
            # 1. Load project with all result relationships
            stmt = (
                select(Project)
                .where(Project.id == uuid.UUID(project_id))
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
            project = (await db.execute(stmt)).scalar_one_or_none()

            if not project:
                err = f"Project {project_id} not found — aborting worker job."
                logger.error(err)
                raise RuntimeError(err)

            # 2. Run the orchestrator pipeline
            orchestrator = _get_orchestrator()
            session = await orchestrator.execute_run(
                db=db,
                project=project,
                correlation_id=correlation_id,
                target_stage=target_stage,
                start_from_stage=start_from_stage,
            )

            logger.info(
                f"[Worker] Pipeline completed | project={project_id} "
                f"status={session.status} progress={session.progress_percentage}%"
            )

            return {
                "success": True,
                "session_id": str(session.id),
                "status": session.status,
                "progress": float(session.progress_percentage),
            }

        except Exception as e:
            logger.error(
                f"[Worker] Pipeline crashed for project {project_id}",
                exc_info=e,
            )
            await db.rollback()
            try:
                session_stmt = (
                    select(GenerationSession)
                    .where(GenerationSession.project_id == uuid.UUID(project_id))
                    .order_by(GenerationSession.created_at.desc())
                    .limit(1)
                )
                session = (await db.execute(session_stmt)).scalars().first()
                if session and session.status in {"PENDING", "INITIALIZING", "RUNNING"}:
                    session.status = "FAILED"
                    session.error_message = f"Pipeline worker crashed: {e}"
                    await db.commit()
                    await _publish_event(
                        f"project:run:{project_id}:stream",
                        {
                            "event_type": "workflow:failed",
                            "project_id": project_id,
                            "session_id": str(session.id),
                            "error_info": {"error_message": session.error_message},
                        },
                    )
            except Exception as status_error:
                await db.rollback()
                logger.error(
                    f"[Worker] Could not persist failed status for project {project_id}",
                    exc_info=status_error,
                )
            return {"success": False, "error": str(e)}
