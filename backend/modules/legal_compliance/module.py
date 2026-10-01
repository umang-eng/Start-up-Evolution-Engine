from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.ollama import ollama_adapter
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

    PROMPT_TEMPLATE = """Generate a concise Legal & Compliance Document Pack for this startup.
Startup Concept: {{ startup_idea }}
Industry: {{ industry }}
Target Region: {{ region }}
DNA Profile: {{ dna }}
Cost Structure: {{ cost }}

{{ registration_data_block }}

{{ funding_data_block }}

{{ compliance_data_block }}

Using the real-time data above, produce a structured compliance document pack:

1. FUNDING SOURCES: List up to 5 active grants, subsidies, or seed fund schemes. Keep each entry short.

2. REGISTRATION REQUIREMENTS: List up to 8 mandatory registrations, tax registrations, and licenses. Keep each entry short.

3. COMPLIANCE DIRECTORIES: List up to 3 key regulatory agencies.

4. DATA PROTECTION: List applicable data protection and privacy requirements for the industry and region.
Only list a law as mandatory when the startup's activities, data, and geography meet its legal scope.
For example, HIPAA applies only to covered entities/business associates handling protected health information;
it is not a general requirement for industrial machinery software. Mark other laws as conditional and state
what fact would make them apply.
If the US is specified without a state, do not present any one state's registration or tax rules as applicable;
identify the state of formation as an input to verify instead.

5. IP PROTECTION: Recommend practical protection steps for product names, source code, designs, and confidential know-how. Clearly mark jurisdiction-specific rights and filing requirements for counsel verification.

6. SUMMARY: Write a 2-3 sentence executive summary of the overall legal landscape and compliance budget estimate.

7. COMPLIANCE BUDGET: Provide a total estimated USD cost for all mandatory registrations and initial compliance setup. If official fees are unavailable, label the amount as a planning estimate requiring local verification.

Ensure ALL scheme names, agency names, and URLs are drawn from the real-time search data provided above. If search data is unavailable for any section, clearly note "Data unavailable — verify with local counsel." Return complete JSON and never stop mid-string or mid-object."""

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

    @staticmethod
    def sanitize_output(
        output: dict[str, Any],
        industry: str,
        region: str,
        research_sources: str = "",
    ) -> dict[str, Any]:
        """Remove jurisdictionally unsupported and ungrounded legal assertions."""
        data = dict(output)
        sources = research_sources.casefold()
        region_code = (region or "").strip().upper()
        industry_text = industry.casefold()
        healthcare = any(term in industry_text for term in ("health", "medical", "clinical", "biotech"))

        def supported(name: str) -> bool:
            return bool(sources and name and name.casefold() in sources)

        def text_of(item: dict[str, Any]) -> str:
            return " ".join(str(value) for value in item.values()).casefold()

        funding_sources = data.get("funding_sources", [])
        if not sources:
            funding_sources = []
        else:
            funding_sources = [
                item for item in funding_sources
                if isinstance(item, dict)
                and supported(str(item.get("scheme_name", "")))
                and not (
                    region_code == "US"
                    and any(term in text_of(item) for term in ("california", "state of"))
                )
                and not (
                    any(name in str(item.get("scheme_name", "")).casefold() for name in ("masschallenge", "y combinator"))
                    and str(item.get("scheme_type", "")).upper() in {"GRANT", "SUBSIDY", "SEED_FUND", "GOVERNMENT_SCHEME"}
                )
            ]
        data["funding_sources"] = funding_sources

        requirements = data.get("registration_requirements", [])
        licenses = data.get("industry_specific_licenses", [])
        directories = data.get("compliance_directories", [])
        if not sources:
            requirements = []
            licenses = []
            directories = []
        else:
            def applicable_item(item: dict[str, Any]) -> bool:
                text = text_of(item)
                if not supported(str(item.get("requirement_name") or item.get("agency_name") or "")):
                    return False
                if region_code == "US" and any(
                    term in text for term in ("california", "ccpa", "cpra", "state business license", "state sales tax")
                ):
                    return False
                if not healthcare and any(term in text for term in ("hipaa", "health and human services", "hhs")):
                    return False
                return True

            requirements = [item for item in requirements if isinstance(item, dict) and applicable_item(item)]
            licenses = [item for item in licenses if isinstance(item, dict) and applicable_item(item)]
            directories = [item for item in directories if isinstance(item, dict) and applicable_item(item)]
        data["registration_requirements"] = requirements
        data["industry_specific_licenses"] = licenses
        data["compliance_directories"] = directories

        privacy = data.get("data_protection_requirements", [])
        safe_privacy = []
        for item in privacy if isinstance(privacy, list) else []:
            statement = str(item)
            lower = statement.casefold()
            if not healthcare and any(term in lower for term in ("hipaa", "hhs")):
                continue
            if region_code == "US" and any(term in lower for term in ("california", "ccpa", "cpra")):
                continue
            if not sources and any(term in lower for term in ("gdpr", "hipaa", "ccpa", "cpra")):
                continue
            safe_privacy.append(statement)
        if not safe_privacy:
            safe_privacy = [
                "Use data minimization, access controls, retention/deletion rules, and a breach-response process; identify applicable privacy laws after confirming customer locations and data flows."
            ]
        if region_code == "US":
            safe_privacy.append(
                "State privacy and business rules depend on the state of formation, customer locations, and data processed; no state-specific requirement is asserted here."
            )
        data["data_protection_requirements"] = list(dict.fromkeys(safe_privacy))

        summary = str(data.get("summary", ""))
        if not sources or any(term in summary.casefold() for term in ("california", "hipaa", "ccpa", "cpra")):
            data["summary"] = (
                "This is general planning guidance, not legal advice. Entity, tax, licensing, privacy, and funding requirements "
                "depend on the chosen jurisdiction, business activities, and data processed; verify them with official authorities "
                "or qualified local counsel before acting."
            )
        data["estimated_compliance_budget_usd"] = 0
        return data

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
        legal_output: LegalComplianceOutput = await ollama_adapter.generate(
            prompt=rendered_prompt,
            schema=LegalComplianceOutput,
            system_instruction=system_instruction,
        )

        research_sources = "\n".join((reg_block, fund_block, comp_block))
        output_dict = self.sanitize_output(
            legal_output.model_dump(),
            project.industry or context.get("dna", {}).get("category", "technology"),
            getattr(project, "region", None) or "US",
            research_sources,
        )
        output_dict["_research_sources"] = research_sources
        if not output_dict.get("ip_protection"):
            output_dict["ip_protection"] = [
                {
                    "asset": "Product and company names",
                    "protection_type": "Search for conflicting marks; ask local counsel whether and where trademark registration is appropriate.",
                    "status": "review",
                },
                {
                    "asset": "Source code, content, and visual designs",
                    "protection_type": "Maintain authorship and assignment records; confirm applicable copyright ownership and registration rules with local counsel.",
                    "status": "review",
                },
                {
                    "asset": "Confidential business information",
                    "protection_type": "Restrict access and use written confidentiality and invention-assignment terms reviewed for the target jurisdiction.",
                    "status": "review",
                },
            ]
        if not output_dict.get("data_protection_requirements"):
            output_dict["data_protection_requirements"] = [
                "Publish a privacy notice describing collected data, purposes, retention, sharing, and user rights; have local counsel confirm jurisdiction-specific requirements.",
                "Collect only necessary personal data, restrict access, define deletion and breach-response procedures, and review processor agreements before launch.",
            ]
        if not output_dict.get("summary"):
            output_dict["summary"] = (
                f"Requirements depend on the startup's activities, data use, and target region ({getattr(project, 'region', None) or 'US'}). "
                "Treat listed registrations and costs as planning guidance until confirmed with the relevant authority or local counsel."
            )
        if not float(output_dict.get("estimated_compliance_budget_usd", 0) or 0):
            logger.warning(
                "[LegalCompliance] No verified fee total was returned; the budget remains unverified."
            )

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
        return {key: value for key, value in output_dict.items() if key != "_research_sources"}
