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
    """Generates dynamic product feature catalogs scaled by startup complexity."""

    SYSTEM_INSTRUCTION = """You are a distinguished Principal Product Manager and Enterprise Software Architect who has built platforms at Stripe, Google, and successful unicorns. You translate high-level business DNA profiles into production-ready product feature catalogs (PRDs) with technical clarity.

Your feature catalogs must be proportional to startup complexity:
- Simple B2C apps: 5-8 features
- B2B SaaS: 8-12 features
- Platform/marketplace: 10-15 features
- Enterprise/DeepTech: 12-20 features

Every feature must include user stories and success metrics. Do not pad with trivial features."""

    PROMPT_TEMPLATE = """Translate the strategic business profile of this startup into a comprehensive, hierarchical product feature catalog.

Predecessor Stage Outputs (DNA Context):
Startup Concept: {{ startup_idea }}
Business Model & Revenue Streams: {{ dna.business_model }}
Value Proposition Core: {{ dna.value_proposition }}
Unique Selling Proposition (USP): {{ dna.usp }}
Market Opportunity: {{ dna.market_size_estimate }}
Complexity Score: {{ dna.scores.complexity }}
Key Competitors: {{ dna.competitor_landscape }}

Based on the DNA complexity score and market context, generate 5-20 features:

1. Core features (MUST_HAVE): Absolute must-haves for MVP launch. Every core feature needs a user story.
2. Advanced features (SHOULD_HAVE): Competitive differentiation features.
3. Future features (COULD_HAVE): Long-term vision features for post-launch.
4. Competitive features: Features specifically designed to counter identified competitors.
5. Growth features: Features that enable scaling and market expansion.

For EACH feature provide:
- Unique ID (e.g. FEAT-001)
- Clear functional description (2-3 sentences)
- User stories in "As a [user], I want [X] so that [Y]" format
- Business value: why this feature matters
- Complexity (LOW/MEDIUM/HIGH) and effort estimate (XS/S/M/L/XL)
- Dependencies on other features (FEAT-XXX IDs)
- Success metrics: how to measure this feature works post-launch

Also provide:
- Non-functional requirements (NFRs): performance, security, scalability needs
- Technical risks: known implementation challenges
- Technology stack recommendations

Ensure all outputs strictly adhere to the requested JSON schema."""

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Loads prompt configs, validates predecessor models, runs AI scopes, and upserts feature results."""
        logger.info(f"Running Feature Extraction Module for project: {project.id}")

        # 1. Enforce requirement validation: dna context must be populated
        dna_context = context.get("dna")
        if not dna_context:
            raise BaseBusinessException(
                message="DNA context is missing. Feature Extraction depends on completed DNA records.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400,
            )

        # 2. Compile templates variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
        }

        # 3. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 4. Invoke LLM with structured output model validation
        feature_output: FeatureExtractorOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=FeatureExtractorOutput,
            system_instruction=system_instruction,
        )

        output_dict = feature_output.model_dump()

        # 5. Database persistence upsert logic
        stmt = select(FeatureResult).where(FeatureResult.project_id == project.id)
        result = await db.execute(stmt)
        feature_record = result.scalars().first()

        if feature_record:
            feature_record.data = output_dict
        else:
            feature_record = FeatureResult(project_id=project.id, data=output_dict)
            db.add(feature_record)

        await db.commit()
        await db.refresh(feature_record)

        logger.info(f"Feature Extraction completed successfully for project: {project.id}")
        return output_dict
