from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import DNAResult
from backend.modules.dna.schemas import DNAOutput
from backend.orchestrator.engine import BaseModule


class DNAModule(BaseModule):
    """Executes business evaluations and builds the startup's DNA profile."""

    SYSTEM_INSTRUCTION = """You are an elite McKinsey senior venture architect, Harvard Business School professor, and seasoned early-stage startup investor. Your goal is to evaluate the feasibility, scalability, and target market validation of a startup concept. Conduct a deep, exhaustive analysis. Your feedback should look like a professional venture review, structured, quantitative, and strategic."""

    PROMPT_TEMPLATE = """Perform an extremely thorough business model and market validation analysis for the following concept:
Startup Idea: {{ startup_idea }}
Industry: {{ industry }}
Target Audience: {{ target_audience }}
Additional Notes: {{ notes }}

Your analysis must cover:
1. Business Model viability: recommend the optimal pricing model (freemium, usage-based, licensing, etc.), unit economics, and customer acquisition strategies.
2. Value Proposition: craft a high-impact, persuasive, and clear value proposition.
3. Unique Selling Proposition (USP): identify the core moat, IP strategy, or defensible advantages.
4. Strategic scores (1-100) with detailed rationales for Market Fit, Feasibility, Scalability, Teamability, Unit Economics, and Innovation.

Ensure all output strictly adheres to the requested JSON schema structure, providing extremely detailed, professional, and actionable insights."""

    async def run(
        self, 
        db: AsyncSession, 
        project: Project, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Runs DNA Analyzer pipeline, saves structured outputs, and updates project metadata."""
        logger.info(f"Running DNA Analyzer Module for project: {project.id}")

        # 1. Compile template variables from payload context
        variables = {
            "startup_idea": project.title,
            "industry": project.industry or "Unspecified",
            "target_audience": project.description or "Unspecified",
            "notes": "None"
        }

        # 2. Render system instructions and prompt templates owned by this module
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables
        )

        # 3. Call AI Layer (Gemini Adapter) for structured validation schema returns
        dna_output: DNAOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=DNAOutput,
            system_instruction=system_instruction
        )

        # Serialize Pydantic output back to dictionary
        output_dict = dna_output.model_dump()

        # 4. Save/Upsert result dataset in PostgreSQL results table
        stmt = select(DNAResult).where(DNAResult.project_id == project.id)
        result = await db.execute(stmt)
        dna_record = result.scalars().first()

        if dna_record:
            dna_record.data = output_dict
        else:
            dna_record = DNAResult(
                project_id=project.id,
                data=output_dict
            )
            db.add(dna_record)

        # Update Project sector metadata tag dynamically if none was suggested
        if not project.industry or project.industry == "Unspecified":
            project.industry = dna_output.category

        await db.commit()
        await db.refresh(dna_record)

        logger.info(f"DNA Analyzer completed successfully for project: {project.id}")
        return output_dict
