from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import LegalComplianceResult
from backend.modules.legal_compliance.schemas import LegalComplianceOutput
from backend.orchestrator.engine import BaseModule
from backend.utils.search import search_provider


class LegalComplianceModule(BaseModule):
    """Post-Blueprint stage: generates a real-time legal & compliance document pack.

    Executes after the Blueprint Composer (Stage 7) and uses live web search to
    produce region-specific funding sources, registration requirements, and
    compliance directories for the startup's target market.
    """

    SYSTEM_INSTRUCTION = """You are an expert corporate legal advisor, startup compliance consultant, and regulatory affairs specialist. You prepare comprehensive legal and compliance documentation packs for early-stage startups entering specific regional markets.

You have access to real-time web search results containing current government schemes, funding programs, registration requirements, and regulatory agency directories. Use this ground truth to:
- List ACTIVE government grants, seed funds, and startup schemes with real URLs
- Specify EXACT registration requirements with issuing authorities and processing timelines
- Reference CURRENT regulatory agencies and their jurisdictions
- Identify industry-specific licenses (e.g., FSSAI for food, SEBI for fintech, CDSCO for pharma)
- Flag data protection requirements applicable to the business model
- Provide realistic compliance budget estimates grounded in actual government fee schedules

Do NOT fabricate schemes or agencies. If a search returned no results for a specific area, state that clearly rather than inventing details."""

    PROMPT_TEMPLATE = """Generate a comprehensive Legal & Compliance Document Pack for this startup.
Startup Concept: {{ startup_idea }}
Industry: {{ industry }}
Target Region: {{ region }}
DNA Profile: {{ dna }}
Cost Structure: {{ cost }}

{{ registration_data_block }}

{{ funding_data_block }}

{{ compliance_data_block }}

Using the real-time data above, produce a structured compliance document pack:

1. FUNDING SOURCES: List 3-8 active grants, subsidies, or seed fund schemes the startup is eligible for in its target region. Include scheme names, types, eligibility criteria, amounts, and application URLs.

2. REGISTRATION REQUIREMENTS: List all mandatory business registrations, tax registrations, and industry licenses. For each, specify the issuing authority, whether it's mandatory, estimated cost, processing timeline, and government portal URL.

3. COMPLIANCE DIRECTORIES: List 1-3 key regulatory agencies the startup will interact with, including jurisdiction and relevant compliance areas.

4. DATA PROTECTION: List applicable data protection and privacy requirements for the industry and region.

5. SUMMARY: Write a 2-3 sentence executive summary of the overall legal landscape and compliance budget estimate.

6. COMPLIANCE BUDGET: Provide a total estimated USD cost for all mandatory registrations and initial compliance setup.

Ensure ALL scheme names, agency names, and URLs are drawn from the real-time search data provided above. If search data is unavailable for any section, clearly note "Data unavailable — verify with local counsel." """

    # ── Search queries for legal/compliance grounding ─────────────
    REGISTRATION_SEARCH_QUERIES = [
        "business registration requirements {region} {year} startup company formation",
        "industry license permit requirements {industry} {region} {year}",
    ]
    FUNDING_SEARCH_QUERIES = [
        "startup government grant seed fund scheme {region} {year} {industry}",
        "tax incentive exemption startup {region} {year}",
    ]
    COMPLIANCE_SEARCH_QUERIES = [
        "data protection privacy law compliance requirements {region} {industry} {year}",
        "regulatory agency compliance body {industry} {region} {year}",
    ]

    async def _fetch_realtime_data(
        self, project: Project, context: dict[str, Any]
    ) -> tuple[str, str, str]:
        """Execute parallel searches for registration, funding, and compliance data.

        Returns:
            (registration_block, funding_block, compliance_block) formatted for LLM injection
        """
        industry = project.industry or context.get("dna", {}).get("category", "technology")
        region = getattr(project, "region", None) or "US"
        year = "2026"

        if not search_provider.is_configured:
            logger.warning("[LegalCompliance] Search provider not configured — using LLM-only analysis")
            empty_market = "[REAL-TIME_MARKET_DATA] Real-time data unavailable.[/REAL-TIME_MARKET_DATA]"
            empty_funding = "[REAL-TIME_FUNDING_DATA] Real-time data unavailable.[/REAL-TIME_FUNDING_DATA]"
            return empty_market, empty_funding, empty_funding

        reg_queries = [
            q.format(industry=industry, region=region, year=year)
            for q in self.REGISTRATION_SEARCH_QUERIES
        ]
        fund_queries = [
            q.format(industry=industry, region=region, year=year)
            for q in self.FUNDING_SEARCH_QUERIES
        ]
        comp_queries = [
            q.format(industry=industry, region=region, year=year)
            for q in self.COMPLIANCE_SEARCH_QUERIES
        ]

        all_queries = reg_queries + fund_queries + comp_queries
        responses = await search_provider.search_multi(
            queries=all_queries,
            region=region,
            industry=industry,
            max_results_per_query=3,
        )

        reg_responses = responses[: len(reg_queries)]
        fund_responses = responses[len(reg_queries): len(reg_queries) + len(fund_queries)]
        comp_responses = responses[len(reg_queries) + len(fund_queries):]

        reg_block = search_provider.format_for_llm(reg_responses)
        fund_block = search_provider.format_grants(fund_responses)
        comp_block = search_provider.format_compliance(comp_responses)

        logger.info(
            f"[LegalCompliance] Injected real-time data for project {project.id}: "
            f"reg={sum(1 for r in reg_responses if r.success)} queries, "
            f"fund={sum(1 for r in fund_responses if r.success)} queries, "
            f"comp={sum(1 for r in comp_responses if r.success)} queries"
        )

        return reg_block, fund_block, comp_block

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validates inputs, fetches real-time compliance data, renders prompt, generates legal doc pack."""
        logger.info(f"Running Legal & Compliance Module for project: {project.id}")

        # 1. Enforce requirement validation — all prior stages must be complete
        dna_context = context.get("dna")
        cost_context = context.get("cost")
        if not dna_context or not cost_context:
            raise BaseBusinessException(
                message="DNA and Cost contexts are required to run the Legal & Compliance Generator.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400,
            )

        # 2. Fetch real-time compliance data
        reg_block, fund_block, comp_block = await self._fetch_realtime_data(project, context)

        # 3. Compile template variables
        variables = {
            "startup_idea": project.title,
            "industry": project.industry or "technology",
            "region": getattr(project, "region", None) or "US",
            "dna": dna_context,
            "cost": cost_context,
            "registration_data_block": reg_block,
            "funding_data_block": fund_block,
            "compliance_data_block": comp_block,
        }

        # 4. Render system instructions and prompt templates
        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        # 5. Invoke LLM structured validation
        legal_output: LegalComplianceOutput = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=LegalComplianceOutput,
            system_instruction=system_instruction,
        )

        output_dict = legal_output.model_dump()

        # 6. Database persistence upsert logic
        stmt = select(LegalComplianceResult).where(LegalComplianceResult.project_id == project.id)
        result = await db.execute(stmt)
        legal_record = result.scalars().first()

        if legal_record:
            legal_record.data = output_dict
        else:
            legal_record = LegalComplianceResult(project_id=project.id, data=output_dict)
            db.add(legal_record)

        await db.commit()
        await db.refresh(legal_record)

        logger.info(f"Legal & Compliance Module completed successfully for project: {project.id}")
        return output_dict
