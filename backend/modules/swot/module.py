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
from backend.utils.search import search_provider


class SWOTModule(BaseModule):
    """Generates strategic SWOT threat/opportunity evaluations with real-time market grounding."""

    SYSTEM_INSTRUCTION = """You are an experienced startup accelerator director, venture capitalist, and risk analyst. You conduct rigorous SWOT (Strengths, Weaknesses, Opportunities, Threats) matrices and formulate actionable risk mitigation strategies that map directly to roadmap execution.

You have access to real-time market data, competitive intelligence, funding schemes, and regulatory developments fetched from live web sources. Use this ground truth to:
- Identify actual government schemes, grants, and subsidies the startup can apply for
- Reference real market trends, competitor moves, and regulatory changes
- Ground your opportunities and threats in verified current events, not hypotheticals
- Cite specific schemes, programs, or market developments by name when relevant
- Assess competitor positioning based on real market data"""

    PROMPT_TEMPLATE = """Perform an exhaustive strategic SWOT risk matrix evaluation.

Predecessor Stage Outputs:
Startup Concept: {{ startup_idea }}
DNA Viability Profile: {{ dna }}
Feature Count: {{ features.features | length }} features
Development Roadmap Phases: {{ roadmap }}
Hiring & Org Structure: {{ team }}

{{ market_data_block }}

{{ funding_data_block }}

Using the real-time market data above (labeled [REAL-TIME_MARKET_DATA] and [REAL-TIME_FUNDING_DATA]), ground your analysis:

Identify:
1. Exactly 2 Core Strengths — internal advantages with specific evidence.
2. Exactly 2 Core Weaknesses — internal gaps with specific evidence.
3. Exactly 2 Market Opportunities — must reference specific market trends, funding programs, or competitive gaps from the real-time data.
4. Exactly 2 Active Threats — must reference specific regulatory risks, competitor moves, or market headwinds from the real-time data.

For each threat, provide:
- Impact (1=Low, 2=Medium, 3=High)
- Probability (1=Low, 2=Medium, 3=High)
- Severity will be computed automatically as impact × probability
- Affected area: MARKET, TECHNICAL, FINANCIAL, REGULATORY, or COMPETITIVE
- Concrete mitigation strategy

Formulate Actionable Strategies:
- Map a clear, concrete, and actionable Mitigation strategy for each threat
- Provide a founder action plan with 3-5 strategic items across 4 time horizons

Additional Analysis:
- Competitor Positioning: where this startup stands vs real competitors
- Market Validation Required: what the founder must validate before proceeding
- Biggest Assumption: the single riskiest assumption the business depends on

Ensure the output conforms strictly to the requested JSON schema, providing strategic value grounded in verified real-time intelligence."""

    # ── Search queries for SWOT grounding ────────────────────────
    MARKET_SEARCH_QUERIES = [
        "{industry} market trends {year} opportunities startups",
        "{industry} competitive landscape emerging players {year}",
    ]
    FUNDING_SEARCH_QUERIES = [
        "government startup grants schemes {industry} {year}",
        "venture capital funding trends {industry} {year}",
    ]

    async def _fetch_realtime_data(
        self, project: Project, context: dict[str, Any]
    ) -> tuple[str, str]:
        """Execute parallel searches for market data and funding schemes."""
        industry = project.industry or context.get("dna", {}).get("category", "technology")
        region = getattr(project, "region", None) or "US"
        year = "2026"

        if not search_provider.is_configured:
            logger.warning("[SWOT] Search provider not configured — using LLM-only analysis")
            return (
                "[REAL-TIME_MARKET_DATA] Real-time market data unavailable. Analyze based on general knowledge.[/REAL-TIME_MARKET_DATA]",
                "[REAL-TIME_FUNDING_DATA] Real-time funding data unavailable. Analyze based on general knowledge.[/REAL-TIME_FUNDING_DATA]",
            )

        market_queries = [
            q.format(industry=industry, year=year) for q in self.MARKET_SEARCH_QUERIES
        ]
        funding_queries = [
            q.format(industry=industry, year=year) for q in self.FUNDING_SEARCH_QUERIES
        ]

        all_queries = market_queries + funding_queries
        responses = await search_provider.search_multi(
            queries=all_queries,
            region=region,
            industry=industry,
            max_results_per_query=3,
        )

        market_responses = responses[: len(market_queries)]
        funding_responses = responses[len(market_queries):]

        market_block = search_provider.format_for_llm(market_responses)
        funding_block = search_provider.format_grants(funding_responses)

        logger.info(
            f"[SWOT] Injected real-time data for project {project.id}: "
            f"market={sum(1 for r in market_responses if r.success)} queries, "
            f"funding={sum(1 for r in funding_responses if r.success)} queries"
        )

        return market_block, funding_block

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validates inputs, fetches real-time market data, renders prompt, triggers SWOT AI compilation."""
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
                status_code=400,
            )

        # 2. Fetch real-time market data
        market_block, funding_block = await self._fetch_realtime_data(project, context)

        # 3. Compile template variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
            "roadmap": roadmap_context,
            "team": team_context,
            "market_data_block": market_block,
            "funding_data_block": funding_block,
        }

        # 4. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 5. Invoke LLM structured validation
        swot_output: SWOTOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=SWOTOutput,
            system_instruction=system_instruction,
        )

        output_dict = swot_output.model_dump()

        # 6. Database persistence upsert logic
        stmt = select(SWOTResult).where(SWOTResult.project_id == project.id)
        result = await db.execute(stmt)
        swot_record = result.scalars().first()

        if swot_record:
            swot_record.data = output_dict
        else:
            swot_record = SWOTResult(project_id=project.id, data=output_dict)
            db.add(swot_record)

        await db.commit()
        await db.refresh(swot_record)

        logger.info(f"SWOT Generator completed successfully for project: {project.id}")
        return output_dict
