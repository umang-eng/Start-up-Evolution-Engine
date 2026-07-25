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
from backend.utils.search import search_provider


class CostModule(BaseModule):
    """Generates financial models connected to features, roadmap, and team with real-time regional cost data."""

    SYSTEM_INSTRUCTION = """You are an expert startup CFO, venture capital financial analyst, and fractional controller. You construct realistic operational cost models, scenario projections, and calculate funding runway targets with high-fidelity corporate budgeting standards.

You have access to real-time regional cost benchmarks, government subsidies, tax incentives, and industrial policy data fetched from live web sources. Use this ground truth to:
- Reference actual salary benchmarks, cloud pricing, and operational costs for the specific region
- Factor in real government subsidies, tax breaks, and industrial incentives the startup can claim
- Ground your financial projections in verified current market rates, not generic estimates
- Cite specific subsidy schemes, SEZ benefits, or regional cost advantages by name
- Connect costs directly to features and roadmap phases"""

    PROMPT_TEMPLATE = """Build a comprehensive operational cost estimation and cash runway analysis model directly connected to the feature catalog and roadmap.

Predecessor Stage Outputs:
Startup Concept: {{ startup_idea }}
DNA Revenue Model: {{ dna }}
Feature Count: {{ features.features | length }} features
Feature Details: {{ features }}
Development Roadmap: {{ roadmap }}
Hiring Chart & Salaries: {{ team }}
SWOT Risk Parameters: {{ swot }}

{{ cost_benchmark_block }}

{{ subsidy_data_block }}

Using the real-time regional cost data above (labeled [REAL-TIME_MARKET_DATA] and [REAL-TIME_FUNDING_DATA]), ground your financial projections:

1. FEATURE COST BREAKDOWN: For each feature in the catalog, estimate:
   - Development cost based on complexity and effort estimate
   - Estimated weeks to build
   - Primary cost driver

2. PHASE COST BREAKDOWN: For each roadmap phase, estimate:
   - Total phase cost (sum of feature costs + overhead)
   - Major cost items

3. Monthly payroll: use the specific base salaries from the hiring chart, adjusted for regional cost benchmarks.

4. Operational tools & services (OPEX): allocate realistic monthly budgets for: Hosting/Cloud, APIs/LLM usage, Marketing/Sales, Operations/Legal.

5. Budget scenarios:
   - LEAN: skeleton MVP launch, minimum viable team
   - BALANCED: 12-18 months of development, moderate hiring
   - AGGRESSIVE: faster hiring and paid growth
   For each scenario, list key assumptions.

6. Contingency: add 10-30% buffer based on risk level.

7. Break-even estimate: when does the business generate enough revenue to cover costs?

8. Government subsidies and tax incentives from the real-time data.

Ensure the output conforms strictly to the requested JSON schema, ensuring financial calculations are clean and balance correctly."""

    # ── Search queries for cost grounding ─────────────────────────
    COST_SEARCH_QUERIES = [
        "{industry} startup operational costs {region} {year} benchmarks",
        "cloud hosting API pricing {industry} startup {year}",
    ]
    SUBSIDY_SEARCH_QUERIES = [
        "government startup subsidy scheme {region} {year} tax incentive",
        "MSME registration benefits {region} industrial policy {year}",
    ]

    async def _fetch_realtime_data(
        self, project: Project, context: dict[str, Any]
    ) -> tuple[str, str]:
        """Execute parallel searches for cost benchmarks and subsidies."""
        industry = project.industry or context.get("dna", {}).get("category", "technology")
        region = getattr(project, "region", None) or "US"
        year = "2026"

        if not search_provider.is_configured:
            logger.warning("[Cost] Search provider not configured — using LLM-only estimation")
            return (
                "[REAL-TIME_MARKET_DATA] Real-time cost data unavailable. Estimate based on general knowledge.[/REAL-TIME_MARKET_DATA]",
                "[REAL-TIME_FUNDING_DATA] Real-time subsidy data unavailable. Estimate based on general knowledge.[/REAL-TIME_FUNDING_DATA]",
            )

        cost_queries = [
            q.format(industry=industry, region=region, year=year)
            for q in self.COST_SEARCH_QUERIES
        ]
        subsidy_queries = [
            q.format(industry=industry, region=region, year=year)
            for q in self.SUBSIDY_SEARCH_QUERIES
        ]

        all_queries = cost_queries + subsidy_queries
        responses = await search_provider.search_multi(
            queries=all_queries,
            region=region,
            industry=industry,
            max_results_per_query=3,
        )

        cost_responses = responses[: len(cost_queries)]
        subsidy_responses = responses[len(cost_queries):]

        cost_block = search_provider.format_for_llm(cost_responses)
        subsidy_block = search_provider.format_grants(subsidy_responses)

        logger.info(
            f"[Cost] Injected real-time data for project {project.id}: "
            f"costs={sum(1 for r in cost_responses if r.success)} queries, "
            f"subsidies={sum(1 for r in subsidy_responses if r.success)} queries"
        )

        return cost_block, subsidy_block

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validates input contexts, fetches real-time cost data, renders prompt, executes AI cost estimation."""
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
                status_code=400,
            )

        # 2. Fetch real-time cost and subsidy data
        cost_block, subsidy_block = await self._fetch_realtime_data(project, context)

        # 3. Compile template variables
        variables = {
            "startup_idea": project.title,
            "dna": dna_context,
            "features": features_context,
            "roadmap": roadmap_context,
            "team": team_context,
            "swot": swot_context,
            "cost_benchmark_block": cost_block,
            "subsidy_data_block": subsidy_block,
        }

        # 4. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 5. Invoke LLM structured validation
        cost_output: CostOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=CostOutput,
            system_instruction=system_instruction,
        )

        output_dict = cost_output.model_dump()

        # 6. Database persistence upsert logic
        stmt = select(CostResult).where(CostResult.project_id == project.id)
        result = await db.execute(stmt)
        cost_record = result.scalars().first()

        if cost_record:
            cost_record.data = output_dict
        else:
            cost_record = CostResult(project_id=project.id, data=output_dict)
            db.add(cost_record)

        await db.commit()
        await db.refresh(cost_record)

        logger.info(f"Cost Estimator completed successfully for project: {project.id}")
        return output_dict
