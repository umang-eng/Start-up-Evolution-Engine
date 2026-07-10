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

    SYSTEM_INSTRUCTION = """You are a distinguished Principal Product Manager and Enterprise Software Architect who has built platforms at Stripe, Google, and successful unicorns. You translate high-level business DNA profiles into production-ready product feature catalogs (PRDs) with deep technical clarity, extensive descriptive context, and rigorous system scope."""

    PROMPT_TEMPLATE = """Translate the strategic business profile of this startup into a highly comprehensive, verbose, and exhaustive hierarchical product feature catalog.
Predecessor Stage Outputs (DNA Context):
Startup Concept: {{ startup_idea }}
Business Model & Revenue Streams: {{ dna.business_model }}
Value Proposition Core: {{ dna.value_proposition }}
Unique Selling Proposition (USP): {{ dna.usp }}

For the MVP, design exactly 5 prioritized features in total:
1. Exactly 2 Core features: absolute must-haves for launch.
2. Exactly 1 Advanced feature: features that provide real competitive differentiation.
3. Exactly 1 Future feature: long-term vision features.
4. Exactly 1 Competitive feature: specific features to defend against incumbents.

For each feature, provide:
- An absolute, unique ID (e.g. FEAT-001).
- An extensively detailed functional description (multiple sentences covering core mechanics, UX logic, and technical requirements).
- Development complexity (Low, Medium, High).
- Pre-requisite feature dependencies.

Do NOT limit your text length. Ensure all outputs strictly adhere to the requested JSON schema, ensuring that descriptions are precise, highly verbose, and robust."""

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
