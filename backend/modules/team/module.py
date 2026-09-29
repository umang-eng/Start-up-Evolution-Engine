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

    SYSTEM_INSTRUCTION = """You are a world-class Head of Talent, HR Executive, and startup co-founder advisor. You design organizational charts, hiring paths, and compensation budgets scaled to support aggressive product delivery timelines with realistic, data-driven targets.

Your team plans must be proportional to roadmap complexity:
- Simple roadmap (15-20 tasks): 3-5 roles
- Medium roadmap (20-30 tasks): 5-8 roles
- Complex roadmap (30+ tasks): 8-12 roles

Consider equity compensation, cofounder needs, and hiring risks."""

    PROMPT_TEMPLATE = """Propose a structured hiring roadmap and salary estimations to support the product launch timeline.

Predecessor Stage Outputs:
Startup Concept: {{ startup_idea }}
DNA Focus Areas: {{ dna }}
Feature Count: {{ features.features | length }} features
Development Roadmap: {{ roadmap }}
Total Estimated Weeks: {{ roadmap.total_estimated_weeks }}

Based on the roadmap complexity ({{ roadmap.total_estimated_weeks }} weeks, {{ roadmap.phases | length }} phases), design a team structure:

Define 3-12 roles (scaled to project complexity):
1. Key departments needed based on the feature set
2. Core positions with:
   - Brief responsibilities (1-2 sentences)
   - Required technical/operational skills
   - Target hiring milestone (linked to specific roadmap phases)
   - Estimated salary ranges (USD/year) — realistic for remote/global startup talent
   - Equity offered (0% for early hires, 1-5% for key hires)
   - Hiring rationale (why this role, when needed)
3. Direct reporting structures (who reports to whom using role IDs)
4. Compensation structure: CASH_ONLY, EQUITY_HEAVY, or BALANCED
5. Total equity pool percentage for all hires
6. Cofounder recommendation: is a cofounder needed? What profile?
7. Key hiring risks (talent scarcity, critical role dependency, etc.)

Compute total monthly payroll for cross-validation with Cost module.

Ensure the output conforms strictly to the requested JSON schema, providing role requirements."""

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
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
                status_code=400,
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
            "roadmap": roadmap_context,
        }

        # 3. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 4. Invoke LLM structured validation client
        team_output: TeamOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=TeamOutput,
            system_instruction=system_instruction,
        )

        output_dict = team_output.model_dump()

        # 5. Database persistence upsert logic
        stmt = select(TeamResult).where(TeamResult.project_id == project.id)
        result = await db.execute(stmt)
        team_record = result.scalars().first()

        if team_record:
            team_record.data = output_dict
        else:
            team_record = TeamResult(project_id=project.id, data=output_dict)
            db.add(team_record)

        await db.commit()
        await db.refresh(team_record)

        logger.info(f"Team Structure completed successfully for project: {project.id}")
        return output_dict
