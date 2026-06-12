import json
import uuid
from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cache.redis import redis_manager
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger, workflow_logger
from backend.models.project import Project
from backend.models.workflow import GenerationSession, WorkflowEvent


class BaseModule(ABC):
    """Base interface for all pipeline strategic generation engines."""

    @abstractmethod
    async def run(self, db: AsyncSession, project: Project, context: dict[str, Any]) -> dict[str, Any]:
        """Runs the AI logic of the module and returns the structured output dict."""
        pass


class WorkflowOrchestrator:
    """Orchestrates the multi-stage startup compilation pipeline."""

    def __init__(self) -> None:
        self.modules: dict[str, BaseModule] = {}
        # Pipeline stages mapping name to (stage_num, is_critical)
        self.stages_config = {
            "dna": (1, True),
            "features": (2, True),
            "roadmap": (3, True),
            "team": (4, True),
            "swot": (5, False),  # SWOT failure is non-critical
            "cost": (6, True),
            "blueprint": (7, True)
        }

    def register_module(self, name: str, module: BaseModule) -> None:
        """Register concrete module execution runner."""
        self.modules[name] = module

    async def execute_run(
        self, 
        db: AsyncSession, 
        project: Project, 
        correlation_id: str
    ) -> GenerationSession:
        """Runs the full compilation sequence, updates state, and streams status telemetry."""
        # 1. Initialize Generation Session record
        session = GenerationSession(
            project_id=project.id,
            status="INITIALIZING",
            correlation_id=correlation_id,
            current_stage="init",
            progress_percentage=0.0
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        channel_name = f"project:run:{project.id}:stream"
        await self._publish_event(channel_name, {
            "event_type": "workflow:started",
            "project_id": str(project.id),
            "timestamp": None
        })

        # Stages sequence list in order
        sequence = ["dna", "features", "roadmap", "team", "swot", "cost", "blueprint"]
        total_stages = len(sequence)

        session.status = "RUNNING"
        await db.commit()

        for idx, stage_name in enumerate(sequence):
            stage_num, is_critical = self.stages_config[stage_name]
            progress = round(((idx) / total_stages) * 100, 2)

            # Update Session DB
            session.current_stage = stage_name
            session.progress_percentage = progress
            await db.commit()

            # Emit Module Started Event
            await self._publish_event(channel_name, {
                "event_type": "module:started",
                "project_id": str(project.id),
                "module_info": {
                    "module_name": stage_name,
                    "stage": stage_num,
                    "total_stages": total_stages,
                    "status": "RUNNING"
                }
            })

            # Check module registry
            module_runner = self.modules.get(stage_name)
            if not module_runner:
                # If during initial setup/testing, we fallback or raise
                err_msg = f"Execution module {stage_name} is not registered in the orchestrator."
                workflow_logger.error(err_msg)
                await self._handle_stage_failure(db, session, channel_name, stage_name, is_critical, err_msg)
                if is_critical:
                    return session
                continue

            # Ingest predecessor outputs from Context Manager
            from backend.ai.context import context_manager
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            stmt = select(Project).where(Project.id == project.id).options(
                selectinload(Project.dna_result),
                selectinload(Project.feature_result),
                selectinload(Project.roadmap_result),
                selectinload(Project.team_result),
                selectinload(Project.swot_result),
                selectinload(Project.cost_result)
            )
            project = (await db.execute(stmt)).scalar_one()

            context = context_manager.assemble_context(project)
            context = context_manager.compress_context_payload(context)

            # Set context variables for analytics tracking
            from backend.core.logging import active_project_id_ctx, active_module_name_ctx
            project_id_token = active_project_id_ctx.set(str(project.id))
            module_name_token = active_module_name_ctx.set(stage_name)

            try:
                # Run with Retry Loop (up to 3 times)
                retry_count = 3
                success = False
                result_data = None

                for attempt in range(retry_count):
                    try:
                        # Execute async module logic
                        result_data = await module_runner.run(db, project, context)
                        success = True
                        break
                    except Exception as e:
                        workflow_logger.warning(
                            f"Module {stage_name} failed execution: attempt {attempt + 1}",
                            exc_info=e
                        )
                        if attempt == retry_count - 1:
                            await self._handle_stage_failure(db, session, channel_name, stage_name, is_critical, str(e))
                            if is_critical:
                                return session
            finally:
                active_project_id_ctx.reset(project_id_token)
                active_module_name_ctx.reset(module_name_token)

            if success and result_data:
                # Log event mapping
                event = WorkflowEvent(
                    session_id=session.id,
                    event_type="module:completed",
                    stage=stage_name,
                    payload=result_data
                )
                db.add(event)
                await db.commit()

                # Emit Module Completed Event with structured result
                await self._publish_event(channel_name, {
                    "event_type": "module:completed",
                    "project_id": str(project.id),
                    "module_info": {
                        "module_name": stage_name,
                        "stage": stage_num
                    },
                    "result_info": result_data
                })

        # Pipeline finished successfully
        session.status = "COMPLETED"
        session.progress_percentage = 100.0
        await db.commit()

        await self._publish_event(channel_name, {
            "event_type": "workflow:completed",
            "project_id": str(project.id),
            "timestamp": None
        })

        return session

    async def _handle_stage_failure(
        self, 
        db: AsyncSession, 
        session: GenerationSession, 
        channel_name: str,
        stage_name: str, 
        is_critical: bool,
        error_msg: str
    ) -> None:
        """Processes execution errors, determines if execution halts, and streams errors."""
        session.error_message = error_msg
        
        # Publish module:failed event
        await self._publish_event(channel_name, {
            "event_type": "module:failed",
            "project_id": str(session.project_id),
            "module_info": {
                "module_name": stage_name
            },
            "error_info": {
                "error_code": "STAGE_EXECUTION_FAILURE",
                "error_message": error_msg,
                "is_fatal": is_critical
            }
        })

        if is_critical:
            session.status = "FAILED"
            await db.commit()
            await self._publish_event(channel_name, {
                "event_type": "workflow:failed",
                "project_id": str(session.project_id),
                "error_info": {
                    "error_message": f"Critical step {stage_name} failed compilation: {error_msg}"
                }
            })
        else:
            # Mark partial success status trace and continue
            session.status = "PARTIAL_SUCCESS"
            await db.commit()

    async def _publish_event(self, channel: str, event_data: dict[str, Any]) -> None:
        """Deliver JSON event wrapper to the active Redis channel."""
        try:
            # Add common timestamp fallback
            event_payload = event_data.copy()
            if not event_payload.get("timestamp"):
                from datetime import datetime, timezone
                event_payload["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            await redis_manager.publish(channel, json.dumps(event_payload))
        except Exception as e:
            logger.error(f"Failed to publish streaming event payload to channel {channel}", exc_info=e)


orchestrator = WorkflowOrchestrator()
