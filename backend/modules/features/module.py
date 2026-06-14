from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import FeatureResult
from backend.modules.features.schemas import FeatureExtractorOutput
from backend.orchestrator.engine import BaseModule


class FeatureModule(BaseModule):
    """Generates structured product scope features catalogs from business DNA metrics."""

    SYSTEM_INSTRUCTION = """You are a senior product manager and software architect. 
Translate the strategic business profile of a startup into a product feature catalog."""

    PROMPT_TEMPLATE = """Analyze the concept: {{ startup_idea }}.
DNA business model and value prop details:
Value Proposition: {{ dna.value_proposition }}
USP: {{ dna.usp }}
Revenue Model: {{ dna.business_model }}
Extract all core, advanced, future, and competitive features into the required JSON schema format."""

    async def run(
        self, 
        db: AsyncSession, 
        project: Project, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Loads prompt configs, validates predecessor models, runs AI scopes, and upserts feature results."""
        logger.info(f"Running Feature Extraction Module for project: {project.id}")

        # 1. Enforce requirement validation: dna context must be populated
        dna_context = context.get("dna")
        if not dna_context:
            raise BaseBusinessException(
                message="DNA context is missing. Feature Extraction depends on completed DNA records.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context
        }

        # 3. Render system instructions and prompt templates owned by this module
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables
        )

        # 4. Invoke LLM client with structured output model validation parameters
        feature_output: FeatureExtractorOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=FeatureExtractorOutput,
            system_instruction=system_instruction
        )

        output_dict = feature_output.model_dump()

        # 5. Database persistence upsert logic
        stmt = select(FeatureResult).where(FeatureResult.project_id == project.id)
        result = await db.execute(stmt)
        feature_record = result.scalars().first()

        if feature_record:
            feature_record.data = output_dict
        else:
            feature_record = FeatureResult(
                project_id=project.id,
                data=output_dict
            )
            db.add(feature_record)

        await db.commit()
        await db.refresh(feature_record)

        logger.info(f"Feature Extraction completed successfully for project: {project.id}")
        return output_dict
