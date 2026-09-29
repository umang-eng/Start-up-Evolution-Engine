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
from backend.utils.search import search_provider


class DNAModule(BaseModule):
    """Executes business evaluations and builds the startup's DNA profile with real-time market grounding."""

    SYSTEM_INSTRUCTION = """You are an elite McKinsey senior venture architect, Harvard Business School professor, and seasoned early-stage startup investor. Your goal is to evaluate the feasibility, scalability, and target market validation of a startup concept. Conduct a deep, exhaustive analysis grounded in real market data. Your feedback should look like a professional venture review — structured, quantitative, and strategic.

You have access to real-time market data and competitive intelligence fetched from live web sources. Use this ground truth to:
- Ground your TAM/SAM/SOM estimates in verified market research
- Identify actual competitors and assess their threat level
- Base risk assessments on real market conditions, not hypotheticals
- Reference specific market trends, funding patterns, and competitive dynamics
- Cite data sources when available"""

    PROMPT_TEMPLATE = """Perform an extremely thorough business model and market validation analysis for the following concept:
Startup Idea: {{ startup_idea }}
Industry: {{ industry }}
Target Audience: {{ target_audience }}
Description: {{ description }}

{{ market_data_block }}

{{ competitor_data_block }}

Using the real-time market data above (if available), ground your analysis in verified evidence:

1. Business Model viability: recommend the optimal pricing model (freemium, usage-based, licensing, etc.), unit economics, and customer acquisition strategies.

2. Value Proposition: craft a high-impact, persuasive, and clear value proposition.

3. Unique Selling Proposition (USP): identify the core moat, IP strategy, or defensible advantages.

4. Market Sizing: estimate TAM, SAM, and SOM based on the market data provided. Explain your reasoning.

5. Competitor Analysis: identify 3-5 real competitors from the data. For each, assess their strength and threat level to this startup.

6. Strategic scores (1-100) with detailed rationales for Innovation, Scalability, Complexity, Market Opportunity, Risk Factor, and Competition. Base scores on the evidence provided, not assumptions.

7. Key Risks: identify the top 3-5 risks with brief rationale grounded in market reality.

Generate 2-3 target segments and 3-5 strategic recommendations.
Ensure all output strictly adheres to the requested JSON schema structure, providing professional and actionable insights."""

    # ── Search queries for DNA grounding ──────────────────────────
    MARKET_SEARCH_QUERIES = [
        "{industry} market size TAM 2026 report billion",
        "{industry} market growth rate forecast 2026",
    ]
    COMPETITOR_SEARCH_QUERIES = [
        "{industry} top companies startups competitors 2026",
        "{industry} competitive landscape market share leaders",
    ]

    async def _fetch_realtime_data(
        self, project: Project, context: dict[str, Any]
    ) -> tuple[str, str]:
        """Execute parallel searches for market data and competitors.

        Returns:
            (market_data_block, competitor_data_block) formatted for LLM injection
        """
        industry = project.industry or "technology"
        region = getattr(project, "region", None) or "US"
        year = "2026"

        if not search_provider.is_configured:
            logger.warning("[DNA] Search provider not configured — using LLM-only analysis")
            return (
                "[REAL-TIME_MARKET_DATA] Real-time market data unavailable. Analyze based on general knowledge.[/REAL-TIME_MARKET_DATA]",
                "[REAL-TIME_COMPETITOR_DATA] Real-time competitor data unavailable. Analyze based on general knowledge.[/REAL-TIME_COMPETITOR_DATA]",
            )

        market_queries = [
            q.format(industry=industry, year=year) for q in self.MARKET_SEARCH_QUERIES
        ]
        competitor_queries = [
            q.format(industry=industry, year=year) for q in self.COMPETITOR_SEARCH_QUERIES
        ]

        all_queries = market_queries + competitor_queries
        responses = await search_provider.search_multi(
            queries=all_queries,
            region=region,
            industry=industry,
            max_results_per_query=3,
        )

        market_responses = responses[: len(market_queries)]
        competitor_responses = responses[len(market_queries):]

        market_block = search_provider.format_for_llm(market_responses)
        competitor_block = search_provider.format_for_llm(competitor_responses)

        logger.info(
            f"[DNA] Injected real-time data for project {project.id}: "
            f"market={sum(1 for r in market_responses if r.success)} queries, "
            f"competitors={sum(1 for r in competitor_responses if r.success)} queries"
        )

        return market_block, competitor_block

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Runs DNA Analyzer pipeline with real-time market grounding, saves structured outputs."""
        logger.info(f"Running DNA Analyzer Module for project: {project.id}")

        # 1. Fetch real-time market and competitor data
        market_block, competitor_block = await self._fetch_realtime_data(project, context)

        # 2. Compile template variables from payload context
        variables = {
            "startup_idea": project.title,
            "industry": project.industry or "Unspecified",
            "target_audience": project.description or "Unspecified",
            "description": project.description or "Unspecified",
            "market_data_block": market_block,
            "competitor_data_block": competitor_block,
        }

        # 3. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 4. Call AI Layer for structured validation
        dna_output: DNAOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=DNAOutput,
            system_instruction=system_instruction,
        )

        output_dict = dna_output.model_dump()

        # 5. Save/Upsert result dataset
        stmt = select(DNAResult).where(DNAResult.project_id == project.id)
        result = await db.execute(stmt)
        dna_record = result.scalars().first()

        if dna_record:
            dna_record.data = output_dict
        else:
            dna_record = DNAResult(project_id=project.id, data=output_dict)
            db.add(dna_record)

        # Update Project sector metadata tag dynamically if none was suggested
        if not project.industry or project.industry == "Unspecified":
            project.industry = dna_output.category

        await db.commit()
        await db.refresh(dna_record)

        logger.info(f"DNA Analyzer completed successfully for project: {project.id}")
        return output_dict
