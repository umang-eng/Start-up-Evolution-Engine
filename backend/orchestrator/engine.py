"""
Workflow Orchestrator — 7-Stage Compilation Pipeline Engine

This module defines the core pipeline orchestration logic:
- BaseModule: Abstract interface for each pipeline stage
- WorkflowOrchestrator: Manages stage sequencing, retries, context assembly,
  conditional cache evaluation, and Redis Pub/Sub event streaming

Cache Strategy:
  Before running any module, the orchestrator computes a deterministic
  SHA-256 checksum from the stage's inputs (project base data + all upstream
  results). It then queries the database for an existing result matching
  that checksum. On a hit, the LLM call is skipped entirely.

Parallel Execution:
  Independent stages run concurrently via asyncio.gather:
  - swot + cost (after team completes)
  - blueprint + legal_compliance (after cost completes)
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache.redis import redis_manager
from backend.core.logging import logger, workflow_logger
from backend.models.project import Project
from backend.models.results import (
    DNAResult, FeatureResult, RoadmapResult,
    TeamResult, SWOTResult, CostResult,
    LegalComplianceResult,
)
from backend.models.blueprint import Blueprint
from backend.models.workflow import GenerationSession, WorkflowEvent


# ── Result model lookup table ───────────────────────────────────────
# Maps stage name → SQLAlchemy model class for cache queries

STAGE_RESULT_MODEL_MAP: dict[str, type] = {
    "dna":               DNAResult,
    "features":          FeatureResult,
    "roadmap":           RoadmapResult,
    "team":              TeamResult,
    "swot":              SWOTResult,
    "cost":              CostResult,
    "blueprint":         Blueprint,
    "legal_compliance":  LegalComplianceResult,
}


class BaseModule(ABC):
    """Base interface for all pipeline strategic generation engines."""

    @abstractmethod
    async def run(self, db: AsyncSession, project: Project, context: dict[str, Any]) -> dict[str, Any]:
        """Runs the AI logic of the module and returns the structured output dict."""
        pass

    def render_prompt(self, system_template: str, user_template: str, variables: dict[str, Any]) -> tuple[str, str]:
        """Interpolates variables into the system instruction and prompt templates."""
        from jinja2 import Template
        compressed_vars = self._compress_prompt_variables(variables)
        system_rendered = Template(system_template).render(**compressed_vars)
        user_rendered = Template(user_template).render(**compressed_vars)
        return system_rendered, user_rendered

    def _compress_prompt_variables(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Preserve full structured data between stages — only compress when token limits require it.

        Unlike the old destructive compression, this version keeps all critical fields:
        - DNA: scores, executive_summary, competitor_landscape, key_risks (all downstream-critical)
        - Features: descriptions, user_stories, business_value, dependencies (roadmap needs them)
        - Roadmap: task descriptions, acceptance_criteria, risk_level, feature_ids (team/cost need them)
        - Team: responsibilities, required_skills, equity, salary (cost/blueprint need them)
        - SWOT: mitigations with full severity, founder_actions (blueprint needs them)
        - Cost: full breakdowns, scenarios (blueprint needs them)
        """
        import copy

        compressed = copy.deepcopy(variables)

        # DNA: preserve scores, competitor landscape, key risks — downstream needs all of it
        # Only compress if the description is extremely long
        if "dna" in compressed and isinstance(compressed["dna"], dict):
            dna = compressed["dna"]
            # Keep all fields — DNA is the foundation everything builds on
            # Only truncate extremely long executive_summary if > 2000 chars
            if "executive_summary" in dna and isinstance(dna["executive_summary"], str) and len(dna["executive_summary"]) > 2000:
                dna["executive_summary"] = dna["executive_summary"][:2000] + "... [Truncated]"

        # Features: keep all fields — roadmap needs descriptions, user_stories, dependencies
        # Only compress if feature list is very long (> 25)
        if "features" in compressed and isinstance(compressed["features"], dict):
            features = compressed["features"]
            if "features" in features and isinstance(features["features"], list) and len(features["features"]) > 25:
                features["features"] = features["features"][:25]

        # Roadmap: keep all task fields — team needs role assignments, cost needs duration
        # Only compress if there are too many phases (> 8)
        if "roadmap" in compressed and isinstance(compressed["roadmap"], dict):
            roadmap = compressed["roadmap"]
            if "phases" in roadmap and isinstance(roadmap["phases"], list) and len(roadmap["phases"]) > 8:
                roadmap["phases"] = roadmap["phases"][:8]

        # Team: keep all role fields — cost needs salaries, blueprint needs skills
        # Only compress if there are too many roles (> 15)
        if "team" in compressed and isinstance(compressed["team"], dict):
            team = compressed["team"]
            if "org_chart" in team and isinstance(team["org_chart"], list) and len(team["org_chart"]) > 15:
                team["org_chart"] = team["org_chart"][:15]

        # SWOT: keep all mitigations and actions — blueprint needs full risk data
        # Only compress if lists are extremely long (> 10 items each)
        if "swot" in compressed and isinstance(compressed["swot"], dict):
            swot = compressed["swot"]
            for key in ("strengths", "weaknesses", "opportunities", "threats"):
                if key in swot and isinstance(swot[key], list) and len(swot[key]) > 10:
                    swot[key] = swot[key][:10]

        # Cost: keep full breakdowns — blueprint needs detailed cost analysis
        # Only compress if operational costs list is very long (> 15)
        if "cost" in compressed and isinstance(compressed["cost"], dict):
            cost = compressed["cost"]
            if "operational_costs" in cost and isinstance(cost["operational_costs"], list) and len(cost["operational_costs"]) > 15:
                cost["operational_costs"] = cost["operational_costs"][:15]

        return compressed


class WorkflowOrchestrator:
    """Orchestrates the multi-stage startup compilation pipeline.

    Runs exclusively inside the worker-engine process. Publishes real-time
    progress events to Redis Pub/Sub channels for SSE consumption by the
    API gateway's streaming endpoint.

    Conditional Execution:
        Before each stage, computes an input checksum and compares it against
        the stored checksum of the existing result. On a match (cache hit),
        the LLM call is skipped entirely and the cached data is used.
    """

    STAGES_ORDER: list[str] = ["dna", "features", "roadmap", "team", "swot", "cost", "blueprint", "legal_compliance"]

    STAGES_CONFIG: dict[str, tuple[int, bool]] = {
        "dna":               (1, True),
        "features":          (2, True),
        "roadmap":           (3, True),
        "team":              (4, True),
        "swot":              (5, False),   # SWOT failure is non-critical
        "cost":              (6, True),
        "blueprint":         (7, True),
        "legal_compliance":  (8, True),    # Post-blueprint legal doc pack
    }

    def __init__(self) -> None:
        self.modules: dict[str, BaseModule] = {}

    def register_module(self, name: str, module: BaseModule) -> None:
        """Register a concrete pipeline stage runner."""
        self.modules[name] = module

    async def execute_run(
        self,
        db: AsyncSession,
        project: Project,
        correlation_id: str,
        target_stage: str | None = None,
    ) -> GenerationSession:
        """Execute the compilation pipeline (full sequence or single stage).

        Lifecycle:
        1. Create or reuse a GenerationSession record
        2. For each stage: compute checksum → check cache → run or skip
        3. Publish terminal event (workflow:completed / workflow:failed)
        4. Return the session for result inspection
        """
        from backend.ai.context import context_manager
        from sqlalchemy.orm import selectinload

        # ── Session initialization ────────────────────────────────
        stmt = (
            select(GenerationSession)
            .where(GenerationSession.project_id == project.id)
            .order_by(GenerationSession.created_at.desc())
        )
        existing_session = (await db.execute(stmt)).scalars().first()

        if existing_session:
            session = existing_session
            session.status = "INITIALIZING"
            session.correlation_id = correlation_id
            session.error_message = None
            session.stage_cache_map = {}
            session.cache_hits = 0
            session.cache_misses = 0
            await db.commit()
            await db.refresh(session)
        else:
            session = GenerationSession(
                project_id=project.id,
                status="INITIALIZING",
                correlation_id=correlation_id,
                current_stage="init",
                progress_percentage=0.0,
                stage_cache_map={},
                cache_hits=0,
                cache_misses=0,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

        channel_name = f"project:run:{project.id}:stream"

        await self._publish_event(channel_name, {
            "event_type": "workflow:started",
            "project_id": str(project.id),
            "session_id": str(session.id),
            "correlation_id": correlation_id,
        })

        # ── Stage sequence resolution ─────────────────────────────
        if target_stage:
            if target_stage not in self.STAGES_CONFIG:
                raise ValueError(f"Invalid stage name: {target_stage}")
            sequence = [target_stage]
        else:
            sequence = list(self.STAGES_ORDER)

        total_stages = len(self.STAGES_ORDER)

        session.status = "RUNNING"
        await db.commit()

        # ── Pre-load project with all relations (cached for entire run) ─
        stmt = (
            select(Project)
            .where(Project.id == project.id)
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
        project = (await db.execute(stmt)).scalar_one()

        # ── Parallel execution groups ─────────────────────────────
        # After team (stage 4) completes: swot + cost can run in parallel
        # After cost completes: blueprint + legal_compliance can run in parallel
        PARALLEL_GROUPS: list[list[str]] = [
            ["dna"],                          # Stage 1
            ["features"],                     # Stage 2
            ["roadmap"],                      # Stage 3
            ["team"],                         # Stage 4
            ["swot", "cost"],                 # Stages 5+6: parallel
            ["blueprint", "legal_compliance"], # Stages 7+8: parallel
        ]

        # Flatten for progress tracking, but execute in groups
        completed_stages: set[str] = set()
        progress_base = 0.0

        for group in PARALLEL_GROUPS:
            # Filter to only stages in our target sequence
            active_stages = [s for s in group if s in sequence and s not in completed_stages]
            if not active_stages:
                continue

            if len(active_stages) == 1:
                # Single stage — run directly
                stage_name = active_stages[0]
                stage_num, is_critical = self.STAGES_CONFIG[stage_name]
                global_idx = self.STAGES_ORDER.index(stage_name)
                progress = round((global_idx / total_stages) * 100, 2)

                session.current_stage = stage_name
                session.progress_percentage = progress
                await db.commit()

                success = await self._run_single_stage(
                    db, session, project, channel_name, stage_name, is_critical, total_stages
                )
                completed_stages.add(stage_name)

                if not success and is_critical:
                    return session

                # Refresh project after stage completion
                stmt = (
                    select(Project)
                    .where(Project.id == project.id)
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
                project = (await db.execute(stmt)).scalar_one()

            else:
                # Multiple stages — run in parallel
                logger.info(f"[Pipeline] Running parallel group: {active_stages}")

                # Update progress for the first stage in the group
                first_stage = active_stages[0]
                global_idx = self.STAGES_ORDER.index(first_stage)
                progress = round((global_idx / total_stages) * 100, 2)
                session.current_stage = "+".join(active_stages)
                session.progress_percentage = progress
                await db.commit()

                # Run all stages in parallel
                tasks = [
                    self._run_single_stage(
                        db, session, project, channel_name, stage_name,
                        self.STAGES_CONFIG[stage_name][1], total_stages,
                        parallel=True,
                    )
                    for stage_name in active_stages
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for stage_name, result in zip(active_stages, results):
                    completed_stages.add(stage_name)
                    if isinstance(result, Exception):
                        workflow_logger.error(f"Parallel stage {stage_name} raised: {result}")
                        is_critical = self.STAGES_CONFIG[stage_name][1]
                        await self._handle_stage_failure(
                            db, session, channel_name, stage_name, is_critical, str(result)
                        )
                        if is_critical:
                            return session

                # Refresh project after parallel group
                stmt = (
                    select(Project)
                    .where(Project.id == project.id)
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
                project = (await db.execute(stmt)).scalar_one()

        # ── Pipeline terminal state ───────────────────────────────
        session.status = "COMPLETED"
        if target_stage:
            global_idx = self.STAGES_ORDER.index(target_stage)
            session.progress_percentage = round(((global_idx + 1) / total_stages) * 100, 2)
        else:
            session.progress_percentage = 100.0
        await db.commit()

        await self._publish_event(channel_name, {
            "event_type": "workflow:completed",
            "project_id": str(project.id),
            "session_id": str(session.id),
            "cache_summary": {
                "hits": int(session.cache_hits),
                "misses": int(session.cache_misses),
                "stage_map": session.stage_cache_map,
            },
        })

        return session

    # ── Single Stage Runner (supports parallel execution) ──────────

    async def _run_single_stage(
        self,
        db: AsyncSession,
        session: GenerationSession,
        project: Project,
        channel_name: str,
        stage_name: str,
        is_critical: bool,
        total_stages: int,
        parallel: bool = False,
    ) -> bool:
        """Run a single pipeline stage with caching and retry logic.

        Returns True on success, False on failure.
        """
        from backend.ai.context import context_manager

        stage_num = self.STAGES_CONFIG[stage_name][0]
        global_idx = self.STAGES_ORDER.index(stage_name)

        # Emit module:started
        await self._publish_event(channel_name, {
            "event_type": "module:started",
            "project_id": str(project.id),
            "session_id": str(session.id),
            "module_info": {
                "module_name": stage_name,
                "stage": stage_num,
                "total_stages": total_stages,
                "status": "RUNNING",
                "parallel": parallel,
            },
        })

        # Check module registry
        module_runner = self.modules.get(stage_name)
        if not module_runner:
            err_msg = f"Module '{stage_name}' is not registered in the orchestrator."
            workflow_logger.error(err_msg)
            await self._handle_stage_failure(db, session, channel_name, stage_name, is_critical, err_msg)
            return False

        # Assemble context from predecessor outputs
        context = context_manager.assemble_context(project)
        context = context_manager.compress_context_payload(context)

        # Semantic Checksum Computation
        input_checksum = context_manager.compute_input_checksum(
            stage_name=stage_name,
            project=project,
            context=context,
        )

        # Cache Lookup
        stored_checksum = context_manager.get_stored_checksum(project, stage_name)
        cache_hit = (stored_checksum is not None and stored_checksum == input_checksum)

        if cache_hit:
            logger.info(
                f"[Cache HIT] Stage '{stage_name}' | project={project.id} "
                f"checksum={input_checksum[:12]}… — reusing stored result"
            )
            result_data = await self._load_cached_result(db, stage_name, project.id)
            if result_data is None:
                logger.warning(
                    f"[Cache MISS] Checksum matched but no DB row for stage '{stage_name}' | "
                    f"project={project.id} — falling back to fresh generation"
                )
                cache_hit = False

        if not cache_hit:
            if stored_checksum:
                logger.info(
                    f"[Cache MISS] Stage '{stage_name}' | project={project.id} "
                    f"input={input_checksum[:12]}… stored={stored_checksum[:12]}… — inputs changed"
                )
            else:
                logger.info(
                    f"[Cache MISS] Stage '{stage_name}' | project={project.id} "
                    f"checksum={input_checksum[:12]}… — no prior result"
                )

            from backend.core.logging import active_project_id_ctx, active_module_name_ctx
            project_id_token = active_project_id_ctx.set(str(project.id))
            module_name_token = active_module_name_ctx.set(stage_name)

            try:
                retry_count = 3
                success = False
                result_data = None

                for attempt in range(retry_count):
                    try:
                        result_data = await module_runner.run(db, project, context)
                        success = True
                        break
                    except Exception as e:
                        workflow_logger.warning(
                            f"Module {stage_name} failed: attempt {attempt + 1}/{retry_count}",
                            exc_info=e,
                        )
                        if attempt == retry_count - 1:
                            await self._handle_stage_failure(
                                db, session, channel_name, stage_name, is_critical, str(e)
                            )
                            return False
            finally:
                active_project_id_ctx.reset(project_id_token)
                active_module_name_ctx.reset(module_name_token)

            if not success:
                return False

            await self._save_checksum(db, stage_name, project.id, input_checksum)

        # Stage completion
        cache_status = "hit" if cache_hit else "miss"
        session.cache_hits = int(session.cache_hits) + (1 if cache_hit else 0)
        session.cache_misses = int(session.cache_misses) + (0 if cache_hit else 1)
        if session.stage_cache_map is None:
            session.stage_cache_map = {}
        session.stage_cache_map[stage_name] = cache_status
        await db.commit()

        # Persist event log
        event = WorkflowEvent(
            session_id=session.id,
            event_type="module:completed",
            stage=stage_name,
            payload={
                **(result_data or {}),
                "_cache_status": cache_status,
                "_checksum": input_checksum,
            },
        )
        db.add(event)
        await db.commit()

        # Emit module:completed
        await self._publish_event(channel_name, {
            "event_type": "module:completed",
            "project_id": str(project.id),
            "session_id": str(session.id),
            "module_info": {
                "module_name": stage_name,
                "stage": stage_num,
            },
            "cache_status": cache_status,
            "checksum": input_checksum,
            "result_info": result_data,
        })

        return True

    # ── Cache Helpers ──────────────────────────────────────────────

    async def _load_cached_result(
        self,
        db: AsyncSession,
        stage_name: str,
        project_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Load the stored result data for a given stage from the database."""
        model_class = STAGE_RESULT_MODEL_MAP.get(stage_name)
        if not model_class:
            return None

        stmt = select(model_class).where(model_class.project_id == project_id)
        record = (await db.execute(stmt)).scalars().first()
        if record and record.data:
            return record.data
        return None

    async def _save_checksum(
        self,
        db: AsyncSession,
        stage_name: str,
        project_id: uuid.UUID,
        checksum: str,
    ) -> None:
        """Update the hash_checksum on the existing result record for a stage."""
        model_class = STAGE_RESULT_MODEL_MAP.get(stage_name)
        if not model_class:
            return

        stmt = select(model_class).where(model_class.project_id == project_id)
        record = (await db.execute(stmt)).scalars().first()
        if record:
            record.hash_checksum = checksum
            await db.commit()

    # ── Failure Handling ───────────────────────────────────────────

    async def _handle_stage_failure(
        self,
        db: AsyncSession,
        session: GenerationSession,
        channel_name: str,
        stage_name: str,
        is_critical: bool,
        error_msg: str,
    ) -> None:
        """Handle stage failure: update DB, publish failure events."""
        session.error_message = error_msg

        await self._publish_event(channel_name, {
            "event_type": "module:failed",
            "project_id": str(session.project_id),
            "session_id": str(session.id),
            "module_info": {"module_name": stage_name},
            "error_info": {
                "error_code": "STAGE_EXECUTION_FAILURE",
                "error_message": error_msg,
                "is_fatal": is_critical,
            },
        })

        if is_critical:
            session.status = "FAILED"
            await db.commit()
            await self._publish_event(channel_name, {
                "event_type": "workflow:failed",
                "project_id": str(session.project_id),
                "session_id": str(session.id),
                "error_info": {
                    "error_message": f"Critical stage '{stage_name}' failed: {error_msg}",
                },
            })
        else:
            session.status = "PARTIAL_SUCCESS"
            await db.commit()

    # ── Event Publishing ───────────────────────────────────────────

    async def _publish_event(self, channel: str, event_data: dict[str, Any]) -> None:
        """Publish a JSON event envelope to a Redis Pub/Sub channel."""
        try:
            payload = event_data.copy()
            if not payload.get("timestamp"):
                from datetime import datetime, timezone
                payload["timestamp"] = datetime.now(timezone.utc).isoformat()

            await redis_manager.publish(channel, json.dumps(payload))
        except Exception as e:
            logger.error(f"Failed to publish event to channel {channel}", exc_info=e)
