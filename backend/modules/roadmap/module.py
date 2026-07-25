from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import RoadmapResult
from backend.modules.roadmap.schemas import RoadmapOutput
from backend.orchestrator.engine import BaseModule


class RoadmapModule(BaseModule):
    """Generates execution plan timelines and milestone stages from feature architecture mappings."""

    SYSTEM_INSTRUCTION = """You are an expert Technical Program Manager (TPM) and Agile Coach who has managed large-scale engineering integrations at AWS and Netflix. You convert product feature specifications into highly execution-oriented, logical, and phased delivery roadmaps.

Your roadmaps must be proportional to the feature count and complexity:
- 5-8 features: 3-4 phases, 15-25 tasks total
- 8-12 features: 4-5 phases, 20-30 tasks total
- 12-20 features: 5-6 phases, 25-40 tasks total

Every task must have acceptance criteria, risk level, and critical path marking."""

    PROMPT_TEMPLATE = """Design a comprehensive, phased development roadmap for the startup.

Predecessor Stage Outputs:
Startup Concept: {{ startup_idea }}
DNA Details: {{ dna }}
Feature Catalog: {{ features }}

The feature catalog above contains {{ features.features | length }} features. Scale the roadmap accordingly:

Structure the roadmap into 3-6 chronological phases. For each phase:
1. Define 3-5 specific, action-oriented engineering tasks (link each to FEAT-XXX IDs)
2. Include duration estimates (in weeks) for each task
3. Mark tasks on the critical path (delay = project delay)
4. Define acceptance criteria for each task (definition of done)
5. Assess risk level (LOW/MEDIUM/HIGH) per task
6. Identify key risks specific to this phase
7. Define milestones that act as deployment gates

After all phases, provide:
- Total estimated project duration in weeks
- Critical path: list of task IDs that cannot slip
- Key cross-phase dependencies that could cause cascading delays
- Launch readiness checklist with readiness score

Ensure the output conforms strictly to the requested JSON schema, providing professional, executable milestones."""

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validates predecessor scopes, renders prompts, executes AI timeline models, and persists records."""
        logger.info(f"Running Roadmap Generator Module for project: {project.id}")

        # 1. Enforce requirement validation
        dna_context = context.get("dna")
        features_context = context.get("features")
        if not dna_context or not features_context:
            raise BaseBusinessException(
                message="DNA and Feature context inputs are required to run the Roadmap Generator.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400,
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
        }

        # 3. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 4. Call LLM structured validation client
        roadmap_output: RoadmapOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=RoadmapOutput,
            system_instruction=system_instruction,
        )

        output_dict = roadmap_output.model_dump()

        # 5. DB upsert persistence
        stmt = select(RoadmapResult).where(RoadmapResult.project_id == project.id)
        result = await db.execute(stmt)
        roadmap_record = result.scalars().first()

        if roadmap_record:
            roadmap_record.data = output_dict
        else:
            roadmap_record = RoadmapResult(project_id=project.id, data=output_dict)
            db.add(roadmap_record)

        await db.commit()
        await db.refresh(roadmap_record)

        logger.info(f"Roadmap Generator completed successfully for project: {project.id}")
        return output_dict
