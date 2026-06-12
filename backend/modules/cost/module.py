from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.ai.prompts import prompt_manager
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import CostResult
from backend.modules.cost.schemas import CostOutput
from backend.orchestrator.engine import BaseModule


class CostModule(BaseModule):
    """Generates financial models, scenario projections, and funding requirements analysis."""

    async def run(
        self, 
        db: AsyncSession, 
        project: Project, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Validates input contexts, renders prompt structures, executes AI cost estimation, and commits records."""
        logger.info(f"Running Cost Estimator Module for project: {project.id}")

        # 1. Enforce requirement validation
        dna_context = context.get("dna")
        features_context = context.get("features")
        roadmap_context = context.get("roadmap")
        team_context = context.get("team")
        swot_context = context.get("swot")
        
        if not dna_context or not features_context or not roadmap_context or not team_context or not swot_context:
            raise BaseBusinessException(
                message="DNA, Feature, Roadmap, Team, and SWOT contexts are required to run the Cost Estimator.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
            "roadmap": roadmap_context,
            "team": team_context,
            "swot": swot_context
        }

        # 3. Render prompt instructions
        system_instruction, rendered_prompt = prompt_manager.render_prompt(
            module_name="cost_estimator",
            variables=variables
        )

        # 4. Invoke LLM structured validation client
        cost_output: CostOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=CostOutput,
            system_instruction=system_instruction
        )

        output_dict = cost_output.model_dump()

        # 5. Database persistence upsert logic
        stmt = select(CostResult).where(CostResult.project_id == project.id)
        result = await db.execute(stmt)
        cost_record = result.scalars().first()

        if cost_record:
            cost_record.data = output_dict
        else:
            cost_record = CostResult(
                project_id=project.id,
                data=output_dict
            )
            db.add(cost_record)

        await db.commit()
        await db.refresh(cost_record)

        logger.info(f"Cost Estimator completed successfully for project: {project.id}")
        return output_dict
