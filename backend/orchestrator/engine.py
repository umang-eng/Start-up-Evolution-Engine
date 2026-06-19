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

    def render_prompt(self, system_template: str, user_template: str, variables: dict[str, Any]) -> tuple[str, str]:
        """Interpolates variables into the system instruction and prompt templates."""
        from jinja2 import Template
        compressed_vars = self._compress_prompt_variables(variables)
        system_rendered = Template(system_template).render(**compressed_vars)
        user_rendered = Template(user_template).render(**compressed_vars)
        return system_rendered, user_rendered

    def _compress_prompt_variables(self, variables: dict[str, Any]) -> dict[str, Any]:
        """Recursively compresses context dictionaries specifically for prompt payload reduction."""
        import copy
        
        # Deep copy to avoid modifying original business logic/state dictionaries
        compressed = copy.deepcopy(variables)
        
        # 1. Compress 'dna'
        if "dna" in compressed and isinstance(compressed["dna"], dict):
            dna = compressed["dna"]
            keys_to_keep = ["category", "customer_type", "market_type", "business_model", "revenue_streams", "value_proposition", "usp", "target_segments"]
            compressed["dna"] = {k: dna[k] for k in keys_to_keep if k in dna}

        # 2. Compress 'features'
        if "features" in compressed and isinstance(compressed["features"], dict):
            features = compressed["features"]
            if "features" in features and isinstance(features["features"], list):
                c_feats = []
                for feat in features["features"]:
                    if isinstance(feat, dict):
                        c_feats.append({
                            "id": feat.get("id"),
                            "title": feat.get("title"),
                            "complexity": feat.get("complexity"),
                            "impact": feat.get("impact")
                        })
                    else:
                        c_feats.append(feat)
                compressed["features"] = {"features": c_feats[:15]}

        # 3. Compress 'roadmap'
        if "roadmap" in compressed and isinstance(compressed["roadmap"], dict):
            roadmap = compressed["roadmap"]
            if "phases" in roadmap and isinstance(roadmap["phases"], list):
                c_phases = []
                for phase in roadmap["phases"]:
                    if isinstance(phase, dict):
                        c_phase = {
                            "phase_id": phase.get("phase_id"),
                            "name": phase.get("name"),
                            "duration_months": phase.get("duration_months"),
                            "milestones": phase.get("milestones")
                        }
                        tasks = phase.get("tasks", [])
                        if isinstance(tasks, list):
                            c_tasks = []
                            for t in tasks:
                                if isinstance(t, dict):
                                    c_tasks.append({
                                        "id": t.get("id"),
                                        "title": t.get("title"),
                                        "duration_weeks": t.get("duration_weeks"),
                                        "assigned_role_id": t.get("assigned_role_id")
                                    })
                                else:
                                    c_tasks.append(t)
                            c_phase["tasks"] = c_tasks
                        c_phases.append(c_phase)
                    else:
                        c_phases.append(phase)
                compressed["roadmap"] = {"phases": c_phases}

        # 4. Compress 'team'
        if "team" in compressed and isinstance(compressed["team"], dict):
            team = compressed["team"]
            if "org_chart" in team and isinstance(team["org_chart"], list):
                c_org = []
                for role in team["org_chart"]:
                    if isinstance(role, dict):
                        c_org.append({
                            "role_id": role.get("role_id"),
                            "title": role.get("title"),
                            "department": role.get("department"),
                            "estimated_salary_usd": role.get("estimated_salary_usd"),
                            "hiring_stage": role.get("hiring_stage")
                        })
                    else:
                        c_org.append(role)
                compressed["team"] = {
                    "org_chart": c_org,
                    "recommended_team_size": team.get("recommended_team_size"),
                    "hiring_sequence": team.get("hiring_sequence")
                }

        # 5. Compress 'swot'
        if "swot" in compressed and isinstance(compressed["swot"], dict):
            swot = compressed["swot"]
            c_swot = {}
            for k in ["strengths", "weaknesses", "opportunities", "threats"]:
                if k in swot:
                    c_swot[k] = swot[k]
            if "mitigations" in swot and isinstance(swot["mitigations"], list):
                c_mit = []
                for mit in swot["mitigations"]:
                    if isinstance(mit, dict):
                        c_mit.append({
                            "threat_description": mit.get("threat_description"),
                            "severity": mit.get("severity"),
                            "mitigation_strategy": mit.get("mitigation_strategy")
                        })
                c_swot["mitigations"] = c_mit
            if "founder_actions" in swot and isinstance(swot["founder_actions"], list):
                c_act = []
                for act in swot["founder_actions"]:
                    if isinstance(act, dict):
                        c_act.append({
                            "horizon": act.get("horizon"),
                            "action": act.get("action"),
                            "priority": act.get("priority")
                        })
                c_swot["founder_actions"] = c_act
            compressed["swot"] = c_swot

        # 6. Compress 'cost'
        if "cost" in compressed and isinstance(compressed["cost"], dict):
            cost = compressed["cost"]
            c_cost = {}
            if "operational_costs" in cost and isinstance(cost["operational_costs"], list):
                c_op = []
                for op in cost["operational_costs"]:
                    if isinstance(op, dict):
                        c_op.append({
                            "category": op.get("category"),
                            "monthly_usd": op.get("monthly_usd")
                        })
                c_cost["operational_costs"] = c_op
            if "funding_requirements" in cost:
                c_cost["funding_requirements"] = cost["funding_requirements"]
            compressed["cost"] = c_cost

        return compressed


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
        correlation_id: str,
        target_stage: str | None = None
    ) -> GenerationSession:
        """Runs the compilation sequence (full or single stage), updates state, and streams status telemetry."""
        # Check if there is an existing session
        from sqlalchemy import select
        stmt = select(GenerationSession).where(GenerationSession.project_id == project.id).order_by(GenerationSession.created_at.desc())
        existing_session = (await db.execute(stmt)).scalars().first()

        if existing_session:
            session = existing_session
            session.status = "INITIALIZING"
            session.correlation_id = correlation_id
            session.error_message = None
            await db.commit()
            await db.refresh(session)
        else:
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
        stages_list = ["dna", "features", "roadmap", "team", "swot", "cost", "blueprint"]
        if target_stage:
            if target_stage not in self.stages_config:
                raise ValueError(f"Invalid stage name: {target_stage}")
            sequence = [target_stage]
        else:
            sequence = stages_list

        total_stages = len(stages_list)

        session.status = "RUNNING"
        await db.commit()

        for idx, stage_name in enumerate(sequence):
            stage_num, is_critical = self.stages_config[stage_name]
            # Use global index of the stage in the full sequence for correct progress percentage
            global_idx = stages_list.index(stage_name)
            progress = round(((global_idx) / total_stages) * 100, 2)

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
        if target_stage:
            global_idx = stages_list.index(target_stage)
            session.progress_percentage = round(((global_idx + 1) / total_stages) * 100, 2)
        else:
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
