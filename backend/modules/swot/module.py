from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import SWOTResult
from backend.modules.swot.schemas import SWOTOutput
from backend.orchestrator.engine import BaseModule


class SWOTModule(BaseModule):
    """Generates strategic SWOT threat/opportunity evaluations and founder execution priorities."""

    SYSTEM_INSTRUCTION = """You are an experienced startup accelerator director, venture capitalist, and risk analyst. You conduct highly rigorous, extremely detailed SWOT (Strengths, Weaknesses, Opportunities, Threats) matrices and formulate comprehensive, verbose, actionable risk mitigation strategies that map directly to roadmap execution."""

    PROMPT_TEMPLATE = """Perform an exhaustive, highly detailed strategic SWOT risk matrix evaluation.
Predecessor Stage Outputs (DNA, Roadmap, and Team Context):
Startup Concept: {{ startup_idea }}
DNA Viability Profile: {{ dna }}
Development Roadmap Phases: {{ roadmap }}
Hiring & Org Structure: {{ team }}

Identify and describe in exhaustive detail:
1. Exactly 2 Core Strengths.
2. Exactly 2 Core Weaknesses.
3. Exactly 2 Market Opportunities.
4. Exactly 2 Active Threats.

Formulate Actionable Strategies:
- Map a clear, highly detailed, concrete, and verbose Mitigation strategy for each of the 2 identified Threats. Do NOT keep it brief.
- Provide a highly comprehensive founder action plan outlining strategic next steps with expansive context.

Do NOT limit your text length. Ensure the output conforms strictly to the requested JSON schema, providing deep strategic value and extensive analysis."""

    async def run(
        self, 
        db: AsyncSession, 
        project: Project, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validates inputs, renders prompt variables, triggers SWOT AI compilation, and stores records."""
        logger.info(f"Running SWOT Generator Module for project: {project.id}")

        # 1. Enforce requirement validation
        dna_context = context.get("dna")
        features_context = context.get("features")
        roadmap_context = context.get("roadmap")
        team_context = context.get("team")
        if not dna_context or not features_context or not roadmap_context or not team_context:
            raise BaseBusinessException(
                message="DNA, Feature, Roadmap, and Team contexts are required to run the SWOT Generator.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
            "roadmap": roadmap_context,
            "team": team_context
        }

        # 3. Render system instructions and prompt templates owned by this module
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables
        )

        # 4. Invoke LLM structured validation client
        swot_output: SWOTOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=SWOTOutput,
            system_instruction=system_instruction
        )

        output_dict = swot_output.model_dump()

        # 5. Database persistence upsert logic
        stmt = select(SWOTResult).where(SWOTResult.project_id == project.id)
        result = await db.execute(stmt)
        swot_record = result.scalars().first()

        if swot_record:
            swot_record.data = output_dict
        else:
            swot_record = SWOTResult(
                project_id=project.id,
                data=output_dict
            )
            db.add(swot_record)

        await db.commit()
        await db.refresh(swot_record)

        logger.info(f"SWOT Generator completed successfully for project: {project.id}")
        return output_dict
