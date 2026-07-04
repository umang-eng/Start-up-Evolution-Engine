"""
ARQ Worker Tasks — Background Pipeline Execution

This module defines the task functions that the ARQ worker picks up from the Redis queue.
Each task is a standalone async function that creates its own database session and runs
the orchestrator pipeline stage-by-stage, publishing progress events to Redis Pub/Sub.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Any

from backend.core.logging import logger
from backend.database.session import AsyncSessionLocal
from backend.models.project import Project
from backend.cache.redis import redis_manager


# ── Lazy-loaded orchestrator (avoids import-time side effects) ─────
_orchestrator = None


def _get_orchestrator():
    """Lazily import and cache the orchestrator singleton with registered modules."""
    global _orchestrator
    if _orchestrator is None:
        from backend.orchestrator.engine import WorkflowOrchestrator
        _orchestrator = WorkflowOrchestrator()

        from backend.modules.dna.module import DNAModule
        from backend.modules.features.module import FeatureModule
        from backend.modules.roadmap.module import RoadmapModule
        from backend.modules.team.module import TeamModule
        from backend.modules.swot.module import SWOTModule
        from backend.modules.cost.module import CostModule
        from backend.modules.blueprint.module import BlueprintModule
        from backend.modules.legal_compliance.module import LegalComplianceModule

        _orchestrator.register_module("dna", DNAModule())
        _orchestrator.register_module("features", FeatureModule())
        _orchestrator.register_module("roadmap", RoadmapModule())
        _orchestrator.register_module("team", TeamModule())
        _orchestrator.register_module("swot", SWOTModule())
        _orchestrator.register_module("cost", CostModule())
        _orchestrator.register_module("blueprint", BlueprintModule())
        _orchestrator.register_module("legal_compliance", LegalComplianceModule())

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
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    job_id = ctx.get("job_id", "unknown")
    logger.info(
        f"[Worker] Starting compilation pipeline | job={job_id} "
        f"project={project_id} stage={target_stage or 'all'}"
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
                return {"success": False, "error": err}

            # 2. Run the orchestrator pipeline
            orchestrator = _get_orchestrator()
            session = await orchestrator.execute_run(
                db=db,
                project=project,
                correlation_id=correlation_id,
                target_stage=target_stage,
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
            return {"success": False, "error": str(e)}
