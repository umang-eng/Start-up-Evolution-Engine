from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.ai.prompts import prompt_manager
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import DNAResult
from backend.modules.dna.schemas import DNAOutput
from backend.orchestrator.engine import BaseModule


class DNAModule(BaseModule):
    """Executes business evaluations and builds the startup's DNA profile."""

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

        # 2. Render versioned system instructions and prompt templates
        system_instruction, rendered_prompt = prompt_manager.render_prompt(
            module_name="dna_analyzer",
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
