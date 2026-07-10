from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import CostResult
from backend.modules.cost.schemas import CostOutput
from backend.orchestrator.engine import BaseModule


class CostModule(BaseModule):
    """Generates financial models, scenario projections, and funding requirements analysis."""

    SYSTEM_INSTRUCTION = """You are an expert startup CFO, venture capital financial analyst, and fractional controller. You construct highly detailed, deeply comprehensive operational cost models, scenario projections, and calculate funding runway targets with high-fidelity corporate budgeting standards."""

    PROMPT_TEMPLATE = """Build an expansive, highly comprehensive operational cost estimation and cash runway analysis model.
Predecessor Stage Outputs (DNA, Roadmap, Team, and SWOT Context):
Startup Concept: {{ startup_idea }}
DNA Revenue Model: {{ dna }}
Hiring Chart & Salaries: {{ team }}
SWOT Risk Parameters: {{ swot }}

Calculate and project in extreme detail:
1. Monthly payroll expenses: use the specific base salaries from the hiring chart in the team structure. Provide detailed rationales for each cost item.
2. Operational tools & services (OPEX): allocate realistic monthly budgets for core categories: Hosting/Cloud, APIs/LLM usage, Marketing/Sales, and Operations/Legal. Provide verbose justifications.
3. Scenario funding requirements: estimate overall cash target for Lean (skeleton MVP launch), Balanced (12-18 months of development), and Aggressive (faster hiring and paid growth) scenarios with highly descriptive narratives.
4. Total cash runway target and runway months projection.

Do NOT limit your text length. Ensure the output conforms strictly to the requested JSON schema, ensuring financial calculations are clean, balance correctly, and feature extensive context."""

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

        # 3. Render system instructions and prompt templates owned by this module
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
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
