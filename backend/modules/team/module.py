from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import TeamResult
from backend.modules.team.schemas import TeamOutput
from backend.orchestrator.engine import BaseModule


class TeamModule(BaseModule):
    """Generates organizational hiring structures and role responsibility assignments."""

    SYSTEM_INSTRUCTION = """You are a world-class Head of Talent, HR Executive, and startup co-founder advisor. You design highly expansive, detailed organizational charts, hiring paths, and compensation budgets scaled to support aggressive product delivery timelines with realistic, data-driven targets."""

    PROMPT_TEMPLATE = """Propose a highly structured, comprehensively detailed hiring roadmap and salary estimations to support the product launch timeline.
Predecessor Stage Outputs (DNA and Roadmap Context):
Startup Concept: {{ startup_idea }}
DNA Focus Areas: {{ dna }}
Development Roadmap: {{ roadmap }}

Define an execution-oriented startup structure with exactly 3-4 core positions (e.g. CTO, Senior Developer, PM). Provide exhaustive, highly detailed descriptions of their roles, strategic impacts, and technical requirements. DO NOT keep descriptions brief.
Define:
1. Key departments needed.
2. Core positions with verbose, comprehensive responsibilities and required deep technical expertise.
3. Target hiring milestones (linking each position back to specific roadmap phases where their presence is first required).
4. Estimated base salary ranges (USD/year) scaled realistically for remote/global startup talent (incorporate market rates).
5. Direct reporting structures (who reports to whom using role IDs).

Do NOT limit your text length. Ensure the output conforms strictly to the requested JSON schema, providing deeply descriptive role requirements."""

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

        # 3. Render system instructions and prompt templates owned by this module
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
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
