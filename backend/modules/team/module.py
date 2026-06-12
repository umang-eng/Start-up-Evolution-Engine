from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.ai.prompts import prompt_manager
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import TeamResult
from backend.modules.team.schemas import TeamOutput
from backend.orchestrator.engine import BaseModule


class TeamModule(BaseModule):
    """Generates organizational hiring structures and role responsibility assignments."""

    async def run(
        self, 
        db: AsyncSession, 
        project: Project, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validates predecessor metrics, renders prompts, executes AI hiring charts, and commits records."""
        logger.info(f"Running Team Structure Module for project: {project.id}")

        # 1. Enforce requirement validation
        dna_context = context.get("dna")
        features_context = context.get("features")
        roadmap_context = context.get("roadmap")
        if not dna_context or not features_context or not roadmap_context:
            raise BaseBusinessException(
                message="DNA, Feature, and Roadmap contexts are required to run the Team Structure Generator.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
            "roadmap": roadmap_context
        }

        # 3. Render prompt instructions
        system_instruction, rendered_prompt = prompt_manager.render_prompt(
            module_name="team_structure",
            variables=variables
        )

        # 4. Invoke LLM structured validation client
        team_output: TeamOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=TeamOutput,
            system_instruction=system_instruction
        )

        output_dict = team_output.model_dump()

        # 5. Database persistence upsert logic
        stmt = select(TeamResult).where(TeamResult.project_id == project.id)
        result = await db.execute(stmt)
        team_record = result.scalars().first()

        if team_record:
            team_record.data = output_dict
        else:
            team_record = TeamResult(
                project_id=project.id,
                data=output_dict
            )
            db.add(team_record)

        await db.commit()
        await db.refresh(team_record)

        logger.info(f"Team Structure completed successfully for project: {project.id}")
        return output_dict
