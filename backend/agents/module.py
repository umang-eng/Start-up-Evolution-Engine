"""Agent Mesh — AgentModule: drop-in replacement for BaseModule in the pipeline.

AgentModule wraps the agent mesh (agents + workflows) behind the same
interface as BaseModule. It can be registered in the orchestrator alongside
existing modules and is controlled by the AGENT_MESH_CONFIG feature flags.
"""

from __future__ import annotations

import time
from typing import Any, Type

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base import BaseAgent
from backend.agents.config import AGENT_MESH_CONFIG
from backend.agents.context_bus import AgentContextBus
from backend.agents.types import AgentRole, AgentBudget, StageAgentConfig
from backend.agents.workflows import SequentialWorkflow, ParallelWorkflow, DebateWorkflow
from backend.core.logging import logger
from backend.models.project import Project
from backend.orchestrator.engine import BaseModule


# ── Agent factory ─────────────────────────────────────────────────

def _create_agents_for_stage(
    stage_name: str,
    config: StageAgentConfig,
) -> list[BaseAgent]:
    """Instantiate the agent team for a stage based on config."""
    from backend.agents.agents import (
        ResearcherAgent,
        AnalystAgent,
        SynthesizerAgent,
        ReviewerAgent,
    )

    agent_map: dict[AgentRole, type[BaseAgent]] = {
        AgentRole.RESEARCHER: ResearcherAgent,
        AgentRole.ANALYST: AnalystAgent,
        AgentRole.SYNTHESIZER: SynthesizerAgent,
        AgentRole.REVIEWER: ReviewerAgent,
    }

    agents = []
    for role in config.agents:
        budget = config.budgets.get(role, AgentBudget())
        agent_cls = agent_map.get(role)
        if agent_cls:
            if role == AgentRole.SYNTHESIZER:
                # Synthesizer needs stage-specific schema and prompts
                agent = _create_synthesizer_for_stage(stage_name, budget)
            else:
                agent = agent_cls(budget=budget)
            agents.append(agent)

    return agents


def _create_synthesizer_for_stage(
    stage_name: str,
    budget: AgentBudget,
) -> BaseAgent:
    """Create a SynthesizerAgent with the correct schema and prompts for the stage."""
    from backend.agents.agents.synthesizer import SynthesizerAgent

    # Import stage-specific schemas and prompts
    schemas = _get_stage_schemas(stage_name)
    prompts = _get_stage_prompts(stage_name)

    return SynthesizerAgent(
        output_schema=schemas["output"],
        system_instruction=prompts["system"],
        prompt_template=prompts["user"],
        budget=budget,
    )


def _get_stage_schemas(stage_name: str) -> dict[str, Type[BaseModel] | None]:
    """Return the output schema for a stage."""
    if stage_name == "dna":
        from backend.modules.dna.schemas import DNAOutput
        return {"output": DNAOutput}
    elif stage_name == "features":
        from backend.modules.features.schemas import FeatureOutput
        return {"output": FeatureOutput}
    elif stage_name == "roadmap":
        from backend.modules.roadmap.schemas import RoadmapOutput
        return {"output": RoadmapOutput}
    elif stage_name == "team":
        from backend.modules.team.schemas import TeamOutput
        return {"output": TeamOutput}
    elif stage_name == "swot":
        from backend.modules.swot.schemas import SWOTOutput
        return {"output": SWOTOutput}
    elif stage_name == "cost":
        from backend.modules.cost.schemas import CostOutput
        return {"output": CostOutput}
    elif stage_name == "blueprint":
        from backend.modules.blueprint.schemas import BlueprintOutput
        return {"output": BlueprintOutput}
    elif stage_name == "legal_compliance":
        from backend.modules.legal_compliance.schemas import LegalOutput
        return {"output": LegalOutput}
    return {"output": None}


def _get_stage_prompts(stage_name: str) -> dict[str, str]:
    """Return the system instruction and user prompt template for a stage."""
    # Import the existing module to get its prompts
    if stage_name == "dna":
        from backend.modules.dna.module import DNAModule
        return {"system": DNAModule.SYSTEM_INSTRUCTION, "user": DNAModule.PROMPT_TEMPLATE}
    elif stage_name == "features":
        from backend.modules.features.module import FeatureModule
        return {"system": FeatureModule.SYSTEM_INSTRUCTION, "user": FeatureModule.PROMPT_TEMPLATE}
    elif stage_name == "roadmap":
        from backend.modules.roadmap.module import RoadmapModule
        return {"system": RoadmapModule.SYSTEM_INSTRUCTION, "user": RoadmapModule.PROMPT_TEMPLATE}
    elif stage_name == "team":
        from backend.modules.team.module import TeamModule
        return {"system": TeamModule.SYSTEM_INSTRUCTION, "user": TeamModule.PROMPT_TEMPLATE}
    elif stage_name == "swot":
        from backend.modules.swot.module import SWOTModule
        return {"system": SWOTModule.SYSTEM_INSTRUCTION, "user": SWOTModule.PROMPT_TEMPLATE}
    elif stage_name == "cost":
        from backend.modules.cost.module import CostModule
        return {"system": CostModule.SYSTEM_INSTRUCTION, "user": CostModule.PROMPT_TEMPLATE}
    elif stage_name == "blueprint":
        from backend.modules.blueprint.module import BlueprintModule
        return {"system": BlueprintModule.SYSTEM_INSTRUCTION, "user": BlueprintModule.PROMPT_TEMPLATE}
    elif stage_name == "legal_compliance":
        from backend.modules.legal_compliance.module import LegalComplianceModule
        return {"system": LegalComplianceModule.SYSTEM_INSTRUCTION, "user": LegalComplianceModule.PROMPT_TEMPLATE}
    return {"system": "", "user": ""}


def _get_workflow_for_stage(config: StageAgentConfig):
    """Instantiate the workflow for a stage."""
    if config.workflow == "debate":
        return DebateWorkflow(max_rounds=config.max_debate_rounds)
    elif config.workflow == "parallel":
        return ParallelWorkflow(merge_strategy=config.merge_strategy)
    else:
        return SequentialWorkflow()


# ── AgentModule ───────────────────────────────────────────────────

class AgentModule(BaseModule):
    """Drop-in replacement for existing modules. Uses agent mesh internally.

    The run() method:
    1. Creates the agent team for the stage
    2. Creates the workflow
    3. Runs the workflow with the context and a fresh bus
    4. Persists the result using the same DB pattern as the original module
    """

    def __init__(self, stage_name: str) -> None:
        self.stage_name = stage_name
        self.config = AGENT_MESH_CONFIG.get(stage_name)
        if not self.config:
            raise ValueError(f"No agent mesh config for stage: {stage_name}")

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Run the agent mesh workflow for this stage."""
        start_time = time.monotonic()

        logger.info(
            f"[AgentModule] Running {self.stage_name} with "
            f"workflow={self.config.workflow}, agents={[a.value for a in self.config.agents]}"
        )

        # Build the pipeline context for agents
        agent_context = {
            "project_id": str(project.id),
            "startup_idea": project.title,
            "title": project.title,
            "industry": project.industry or "Unspecified",
            "description": project.description or "Unspecified",
            "target_audience": project.description or "Unspecified",
            "enable_web_research": self.config.enable_web_research,
            "region": getattr(project, "region", None) or "US",
            **context,
        }

        # Create agent team and workflow
        agents = _create_agents_for_stage(self.stage_name, self.config)
        workflow = _get_workflow_for_stage(self.config)
        bus = AgentContextBus()

        # Execute workflow
        result_dict = await workflow.execute(agents, agent_context, bus)

        # Remove internal metadata before persisting
        metadata_keys = [k for k in result_dict if k.startswith("_")]
        metadata = {k: result_dict.pop(k) for k in metadata_keys}

        elapsed = time.monotonic() - start_time
        logger.info(
            f"[AgentModule] Completed {self.stage_name} in {elapsed:.1f}s "
            f"metadata={metadata}"
        )

        # Persist using the same pattern as the original module
        await self._persist_result(db, project, result_dict)

        return result_dict

    async def _persist_result(
        self,
        db: AsyncSession,
        project: Project,
        output_dict: dict[str, Any],
    ) -> None:
        """Persist the result to the database using the same upsert pattern."""
        from backend.models.results import (
            DNAResult, FeatureResult, RoadmapResult,
            TeamResult, SWOTResult, CostResult,
            LegalComplianceResult,
        )
        from backend.models.blueprint import Blueprint

        model_map = {
            "dna": DNAResult,
            "features": FeatureResult,
            "roadmap": RoadmapResult,
            "team": TeamResult,
            "swot": SWOTResult,
            "cost": CostResult,
            "blueprint": Blueprint,
            "legal_compliance": LegalComplianceResult,
        }

        model_class = model_map.get(self.stage_name)
        if not model_class:
            logger.warning(f"[AgentModule] No model class for {self.stage_name}")
            return

        stmt = select(model_class).where(model_class.project_id == project.id)
        result = await db.execute(stmt)
        record = result.scalars().first()

        if record:
            record.data = output_dict
        else:
            record = model_class(project_id=project.id, data=output_dict)
            db.add(record)

        # Update industry from DNA if applicable
        if self.stage_name == "dna" and (not project.industry or project.industry == "Unspecified"):
            category = output_dict.get("category", "")
            if category:
                project.industry = category

        await db.commit()
        await db.refresh(record)
