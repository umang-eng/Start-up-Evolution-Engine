from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.ollama import ollama_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.results import CostResult
from backend.modules.cost.schemas import BudgetScenario, CostOutput, FundingRequirement
from backend.orchestrator.engine import BaseModule
from backend.utils.search import search_provider


EFFORT_WEEKS = {"XS": 1, "S": 2, "M": 3, "L": 6, "XL": 10}


class CostModule(BaseModule):
    """Generates financial models connected to features, roadmap, and team with real-time regional cost data."""

    SYSTEM_INSTRUCTION = """You are an expert startup CFO, venture capital financial analyst, and fractional controller. You construct realistic operational cost models, scenario projections, and calculate funding runway targets with high-fidelity corporate budgeting standards.

You have access to real-time regional cost benchmarks, government subsidies, tax incentives, and industrial policy data fetched from live web sources. Use this ground truth to:
- Reference actual salary benchmarks, cloud pricing, and operational costs for the specific region
- Factor in real government subsidies, tax breaks, and industrial incentives the startup can claim
- Ground your financial projections in verified current market rates, not generic estimates
- Cite specific subsidy schemes, SEZ benefits, or regional cost advantages by name
- Connect costs directly to features and roadmap phases"""

    PROMPT_TEMPLATE = """    Build a concise operational cost estimation and cash runway model directly connected to the feature catalog and roadmap.

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

1. FEATURE COST BREAKDOWN: Include each feature, using one short sentence per item:
   - Development cost based on complexity and effort estimate
   - Estimated weeks to build
   - Primary cost driver

2. PHASE COST BREAKDOWN: Include each roadmap phase with:
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

Keep every description and assumption short. Use at most 8 operational costs,
3 budget scenarios, 12 feature items, and 8 phase items. Return complete JSON;
never stop mid-string or mid-object.

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

    @staticmethod
    def _build_estimates(
        output: CostOutput | dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Replace missing/zero model estimates with traceable estimates from project inputs."""
        data = output.model_dump() if isinstance(output, CostOutput) else dict(output)
        features_data = context.get("features_output") or context.get("features", {})
        features = features_data.get("features", []) if isinstance(features_data, dict) else []
        team = context.get("team_output") or context.get("team", {})
        roles = team.get("org_chart", team.get("roles", [])) if isinstance(team, dict) else []
        salaries = [
            float(role.get("estimated_salary_usd", 0) or 0)
            for role in roles
            if isinstance(role, dict)
        ]
        payroll = float(team.get("total_monthly_payroll_usd", 0) or 0) if isinstance(team, dict) else 0
        if payroll <= 0:
            payroll = sum(salaries) / 12
        if payroll <= 0:
            payroll = max(len(roles), 1) * 6_000

        engineering_salaries = [
            float(role.get("estimated_salary_usd", 0) or 0)
            for role in roles
            if isinstance(role, dict)
            and any(
                token in f"{role.get('department', '')} {role.get('title', '')}".lower()
                for token in ("engineer", "technical", "product", "design", "ai", "developer")
            )
            and float(role.get("estimated_salary_usd", 0) or 0) > 0
        ]
        hourly_rate = (
            sum(engineering_salaries) / len(engineering_salaries) / 2_080 * 1.3
            if engineering_salaries
            else 50.0
        )

        feature_costs = []
        for feature in features[:12]:
            if not isinstance(feature, dict):
                continue
            effort = str(feature.get("effort_estimate", "M")).upper()
            complexity = str(feature.get("complexity", "MEDIUM")).upper()
            weeks = EFFORT_WEEKS.get(effort, 3)
            if complexity == "HIGH" and effort not in {"L", "XL"}:
                weeks += 1
            feature_costs.append({
                "feature_id": str(feature.get("id", feature.get("name", "feature"))),
                "feature_name": str(feature.get("name", "Unnamed feature")),
                "estimated_cost_usd": round(weeks * 40 * hourly_rate),
                "estimated_weeks": weeks,
                "cost_driver": f"{effort} engineering effort at an estimated ${hourly_rate:,.0f}/hour loaded rate",
            })

        mvp_features = [
            item for item, feature in zip(feature_costs, features[:12])
            if isinstance(feature, dict)
            and (
                str(feature.get("priority", "")).upper() == "MUST_HAVE"
                or str(feature.get("category", "")).upper() == "CORE"
            )
        ]
        if not mvp_features:
            mvp_features = feature_costs[: min(5, len(feature_costs))]

        default_costs = [
            ("SALARIES", "Estimated monthly team payroll from the team salary plan", payroll, True),
            ("INFRASTRUCTURE", "Cloud hosting, storage, backups, and monitoring allowance", 300.0, True),
            ("SAAS_TOOLS", "Development, collaboration, and security tools allowance", 150.0, True),
            ("MARKETING", "Initial customer research and launch marketing allowance", 750.0, False),
            ("LEGAL_REGISTRATION", "Ongoing legal and accounting provision; confirm local fees", 250.0, True),
            ("INFRASTRUCTURE", "Third-party APIs and AI usage allowance", 250.0, True),
        ]
        existing_costs = data.get("operational_costs") or []
        existing_by_category = {
            item.get("category"): item
            for item in existing_costs
            if isinstance(item, dict) and float(item.get("monthly_usd", 0) or 0) > 0
        }
        operational_costs = []
        for category, description, monthly, critical in default_costs:
            existing = existing_by_category.get(category)
            if existing and existing not in operational_costs:
                operational_costs.append({
                    **existing,
                    "monthly_usd": round(
                        payroll if category == "SALARIES"
                        else float(existing.get("monthly_usd", 0) or monthly)
                    ),
                    "description": (
                        description if category == "SALARIES"
                        else existing.get("description") or description
                    ),
                    "is_mvp_critical": critical,
                })
                existing_by_category.pop(category, None)
            else:
                operational_costs.append({
                    "category": category,
                    "description": description,
                    "monthly_usd": round(monthly),
                    "is_mvp_critical": critical,
                })
        operational_costs.extend(existing_by_category.values())
        data["operational_costs"] = operational_costs
        data["total_monthly_payroll_usd"] = round(payroll)
        data["feature_cost_breakdown"] = feature_costs

        roadmap = context.get("roadmap_output") or context.get("roadmap", {})
        phases = roadmap.get("phases", []) if isinstance(roadmap, dict) else []
        phase_breakdown = []
        for phase in phases[:8]:
            if not isinstance(phase, dict):
                continue
            duration_months = max(int(phase.get("duration_months", 1) or 1), 1)
            task_feature_ids = {
                feature_id
                for task in phase.get("tasks", [])
                if isinstance(task, dict)
                for feature_id in task.get("feature_ids", [])
            }
            phase_features = [
                item for item in feature_costs
                if item["feature_id"] in task_feature_ids
            ]
            phase_cost = sum(item["estimated_cost_usd"] for item in phase_features)
            if phase_cost == 0 and feature_costs and not task_feature_ids:
                phase_cost = round(sum(item["estimated_cost_usd"] for item in feature_costs) / max(len(phases), 1))
            phase_breakdown.append({
                "phase_id": str(phase.get("phase_id", f"phase_{len(phase_breakdown) + 1}")),
                "phase_name": str(phase.get("name", "Development phase")),
                "estimated_cost_usd": round(phase_cost + payroll * duration_months),
                "duration_weeks": max(duration_months * 4, 1),
                "major_cost_items": ["Team payroll", "Feature engineering effort"],
            })
        data["phase_cost_breakdown"] = phase_breakdown

        overhead = sum(
            float(item["monthly_usd"])
            for item in operational_costs
            if item["category"] != "SALARIES"
        )
        monthly_burn = payroll + overhead
        mvp_build = sum(item["estimated_cost_usd"] for item in mvp_features)
        mvp_estimate = max(mvp_build, payroll * 2) + overhead * 3
        year_one_estimate = monthly_burn * 12 + mvp_build
        funding = data.get("funding_requirements") or {}
        if not isinstance(funding, dict):
            funding = {}
        data["mvp_cost_estimate"] = round(max(float(data.get("mvp_cost_estimate", 0) or 0), mvp_estimate))
        data["year_1_cost_estimate"] = round(max(float(data.get("year_1_cost_estimate", 0) or 0), year_one_estimate))
        funding["minimum_target_usd"] = round(max(float(funding.get("minimum_target_usd", 0) or 0), mvp_estimate + monthly_burn * 6))
        funding["optimal_target_usd"] = round(max(float(funding.get("optimal_target_usd", 0) or 0), mvp_estimate + monthly_burn * 12))
        funding["runway_months"] = max(int(funding.get("runway_months", 0) or 0), 12)
        funding["funding_suitability"] = funding.get("funding_suitability") or (
            "Planning estimate based on the team salary plan, feature effort, and monthly operating allowances; "
            "replace assumptions with vendor quotes and local salary benchmarks."
        )
        data["funding_requirements"] = funding

        scenarios = data.get("budget_scenarios") or []
        scenario_factors = {"LEAN": (0.7, 12), "BALANCED": (1.0, 18), "AGGRESSIVE": (1.6, 24)}
        by_name = {
            str(item.get("name", "")).upper(): item
            for item in scenarios if isinstance(item, dict)
        }
        normalized_scenarios = []
        for name, (factor, runway) in scenario_factors.items():
            existing = by_name.get(name, {})
            burn = max(float(existing.get("monthly_burn_usd", 0) or 0), monthly_burn * factor)
            normalized_scenarios.append({
                **existing,
                "name": name,
                "monthly_burn_usd": round(burn),
                "runway_months": max(int(existing.get("runway_months", 0) or 0), runway),
                "description": existing.get("description") or f"{name.title()} staffing and operating budget using estimated project costs.",
                "assumptions": existing.get("assumptions") or [
                    "Planning estimate; validate salaries, cloud usage, and vendor pricing before committing."
                ],
            })
        data["budget_scenarios"] = normalized_scenarios
        return data

    @classmethod
    def _fallback_output(cls, context: dict[str, Any]) -> dict[str, Any]:
        """Build a labeled, input-derived cost baseline when the model returns invalid JSON."""
        baseline = CostOutput(
            operational_costs=[],
            budget_scenarios=[
                BudgetScenario(
                    name=name,
                    monthly_burn_usd=0,
                    runway_months=runway,
                    description=f"{name.title()} planning baseline; validate assumptions before use.",
                    assumptions=["Derived from project feature, roadmap, and team inputs; not a vendor quote."],
                )
                for name, runway in (("LEAN", 12), ("BALANCED", 18), ("AGGRESSIVE", 24))
            ],
            funding_requirements=FundingRequirement(
                minimum_target_usd=0,
                optimal_target_usd=0,
                runway_months=12,
                funding_suitability=(
                    "Planning baseline derived from the project team, feature, and roadmap inputs. "
                    "Validate salaries, vendor pricing, and local funding eligibility."
                ),
            ),
            mvp_cost_estimate=0,
            year_1_cost_estimate=0,
            financial_risk_level="HIGH",
            contingency_percent=25,
            key_cost_risks=[
                "AI cost output was invalid JSON; validate this input-derived planning baseline before budgeting."
            ],
        )
        return cls._build_estimates(baseline, context)

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
        swot_context = context.get("swot") or {}

        if not dna_context or not features_context or not roadmap_context or not team_context:
            raise BaseBusinessException(
                message="DNA, Feature, Roadmap, and Team contexts are required to run the Cost Estimator.",
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
        try:
            cost_output: CostOutput = await ollama_adapter.generate(
                prompt=rendered_prompt,
                schema=CostOutput,
                system_instruction=system_instruction,
            )
            output_dict = self._build_estimates(cost_output, context)
        except BaseBusinessException as exc:
            if exc.code != "OLLAMA_VALIDATION_ERROR":
                raise
            logger.warning(
                "Cost model returned invalid structured output; using an input-derived planning baseline.",
                exc_info=exc,
            )
            output_dict = self._fallback_output(context)

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
