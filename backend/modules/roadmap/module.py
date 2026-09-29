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

    SYSTEM_INSTRUCTION = """You are a concise Technical Program Manager. Convert the startup feature specification into a practical phased roadmap.

Use exactly 3 phases and 2 short tasks per phase for speed. Keep every string brief.
Every task must have an ID, title, duration, role, risk, and critical-path flag."""

    PROMPT_TEMPLATE = """    Design a concise phased development roadmap for the startup.

Predecessor Stage Outputs:
Startup Concept: {{ startup_idea }}
DNA Details: {{ dna }}
Feature Catalog: {{ features }}

The feature catalog above contains {{ features.features | length }} features. Scale the roadmap accordingly:

Return exactly 3 phases with exactly 2 tasks per phase. Use short descriptions and one acceptance criterion per task.
Include total duration, critical path, dependencies, and a short launch checklist.
Return only the requested JSON object."""

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
