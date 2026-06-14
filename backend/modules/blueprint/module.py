import time
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.gemini import gemini_adapter
from backend.core.exceptions import BaseBusinessException
from backend.core.logging import logger
from backend.models.project import Project
from backend.models.blueprint import Blueprint
from backend.modules.blueprint.schemas import (
    BlueprintOutput, 
    ExecutiveSummary, 
    StartupHealthIndicators, 
    ConflictResolutionLogItem
)
from backend.orchestrator.engine import BaseModule


class BlueprintModule(BaseModule):
    """Aggregates all modules data, executes overrides conflict resolution, and generates unified investor blueprints."""

    SYSTEM_INSTRUCTION = """You are an elite Principal Strategy Consultant and lead document compiler who prepares business plans for Tier-1 VC firms (Sequoia, Benchmark, a16z). You compile separate complex business, product, team, and financial modules into a single, cohesive, highly persuasive executive blueprint."""

    PROMPT_TEMPLATE = """Consolidate and review the entire compiled startup blueprint profile to write executive investor narratives.
Compiled Predecessor Modules:
DNA Profile: {{ dna }}
Product Features Spec: {{ features }}
Project Delivery Roadmap: {{ roadmap }}
Hiring Chart & Reporting: {{ team }}
SWOT Opportunity & Risk: {{ swot }}
OPEX & Financing Projections: {{ cost }}

Synthesize five highly detailed, professional, and convincing executive narrative vectors:
1. Business Summary: Clear problem-solution statement, target audience validation, and business model value.
2. Strategic Focus: The core competitive moat, USP, market positioning, and strategic growth drivers.
3. Execution Plan: Core software feature architecture breakdown, MVP launch milestones, and phase timelines.
4. Financial Outlook: Calculated operational expenses, salary commitments, scenarios, and cash runway targets.
5. Founder Action Plan: Critical immediate tasks, prioritized risk mitigations, and next steps for execution.

Ensure the output conforms strictly to the requested JSON schema, providing maximum strategic narrative quality."""

    async def run(
        self, 
        db: AsyncSession, 
        project: Project, 
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Orchestrates conflict checks, health indexing, narrative compilation, and blueprint DB commits."""
        logger.info(f"Running Blueprint Composer Module for project: {project.id}")

        # 1. Enforce validation of all required context inputs
        dna = context.get("dna")
        features = context.get("features")
        roadmap = context.get("roadmap")
        team = context.get("team")
        swot = context.get("swot")
        cost = context.get("cost")

        if not all([dna, features, roadmap, team, cost]):
            raise BaseBusinessException(
                message="Core modules (DNA, Features, Roadmap, Team, Cost) must complete before Blueprint Composer.",
                code="DEPENDENCY_MISSING_ERROR",
                status_code=400
            )
        # SWOT is non-critical — use empty dict if missing
        if not swot:
            swot = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": [], "mitigations": [], "founder_actions": []}
            logger.warning("SWOT data missing — using empty defaults for Blueprint composition.")

        # 2. Run Conflict Resolution Engine (Applying Stage Priority Override Rules)
        resolved_team, resolved_cost, conflict_logs = self._resolve_conflicts(team, cost)

        # 3. Run Startup Health & Readiness Engine
        health_indicators = self._calculate_health_indicators(dna, features, roadmap, resolved_team, swot, resolved_cost)

        # 4. Invoke Gemini to synthesize narrative Executive Summary
        variables = {
            "dna": dna,
            "features": features,
            "roadmap": roadmap,
            "team": resolved_team,
            "swot": swot,
            "cost": resolved_cost
        }

        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables
        )

        logger.info("Generating narrative Executive Summary...")
        summary_output: ExecutiveSummary = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=ExecutiveSummary,
            system_instruction=system_instruction
        )

        # 5. Compile final Output Payload
        blueprint_data = BlueprintOutput(
            executive_summary=summary_output,
            startup_dna=dna,
            product_architecture=features,
            execution_roadmap=roadmap,
            team_structure=resolved_team,
            swot_analysis=swot,
            financial_plan=resolved_cost,
            health_indicators=health_indicators,
            conflict_resolution_log=conflict_logs
        )

        output_dict = blueprint_data.model_dump()

        # 6. Persist results in PostgreSQL blueprints table
        stmt = select(Blueprint).where(Blueprint.project_id == project.id)
        result = await db.execute(stmt)
        blueprint_record = result.scalars().first()

        if blueprint_record:
            blueprint_record.data = output_dict
            blueprint_record.health_score = health_indicators.composite_score
        else:
            blueprint_record = Blueprint(
                project_id=project.id,
                data=output_dict,
                health_score=health_indicators.composite_score
            )
            db.add(blueprint_record)

        await db.commit()
        await db.refresh(blueprint_record)

        logger.info(f"Blueprint Composer completed successfully for project: {project.id}")
        return output_dict

    def _resolve_conflicts(
        self, 
        team: dict[str, Any], 
        cost: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], list[ConflictResolutionLogItem]]:
        """Applies priority override guidelines (Cost overrides Team values)."""
        conflict_logs: list[ConflictResolutionLogItem] = []
        resolved_team = team.copy()
        resolved_cost = cost.copy()

        # Extract org chart roles payroll costs vs cost projections
        # Example Conflict checking: Compare salaries defined in Org Chart to operational budget settings
        org_chart = resolved_team.get("org_chart", [])
        operational_costs = resolved_cost.get("operational_costs", [])

        # Build maps
        cost_salaries = {c["category"]: c for c in operational_costs if "salary" in c["category"].lower()}
        
        for role in org_chart:
            role_id = role["role_id"]
            title = role["title"]
            est_salary = role.get("estimated_salary_usd", 0)

            # Check if Cost Estimator overrides the salary
            cost_item_key = f"SALARIES_{role_id.upper()}"
            if cost_item_key in cost_salaries:
                cost_salary_val = cost_salaries[cost_item_key]["monthly_usd"] * 12
                if abs(cost_salary_val - est_salary) > 100:  # Mismatch detected
                    original_val = est_salary
                    resolved_val = cost_salary_val
                    
                    # Update lower priority: Org Chart estimates scaled down to comply with Cost limits
                    role["estimated_salary_usd"] = resolved_val

                    conflict_logs.append(
                        ConflictResolutionLogItem(
                            conflict_id=f"CR-{int(time.time())}-{role_id}",
                            field_path=f"team_structure.org_chart.{role_id}.estimated_salary_usd",
                            conflict_type="SALARY_LIMIT_MISMATCH",
                            original_values={"team_module": original_val, "cost_module": resolved_val},
                            resolved_value=resolved_val,
                            override_rule="COST_LIMIT_OVER_TEAM_SALARY",
                            severity="WARNING",
                            log_message=f"Hiring salary for {title} scaled from ${original_val:,.2f} to ${resolved_val:,.2f} to comply with Cost Estimator budget caps."
                        )
                    )

        return resolved_team, resolved_cost, conflict_logs

    def _calculate_health_indicators(
        self,
        dna: dict[str, Any],
        features: dict[str, Any],
        roadmap: dict[str, Any],
        team: dict[str, Any],
        swot: dict[str, Any],
        cost: dict[str, Any]
    ) -> StartupHealthIndicators:
        """Calculates quantitative startup viability and readiness scores."""
        # 1. Execution Readiness (Er)
        # Based on features count vs roadmap tasks mapping
        total_tasks = sum(len(p.get("tasks", [])) for p in roadmap.get("phases", []))
        total_features = len(features.get("features", []))
        execution_readiness = 80.0
        if total_features > 0:
            execution_readiness = min(100.0, max(50.0, 50.0 + (total_tasks / total_features) * 10))

        # 2. Funding Readiness (Fr)
        # Based on year 1 costs and runway target durations
        runway_months = cost.get("funding_requirements", {}).get("runway_months", 12)
        funding_readiness = min(100.0, max(40.0, 40.0 + (runway_months / 18.0) * 60.0))

        # 3. Growth Readiness (Gr)
        # Scale rating parameters
        growth_readiness = min(100.0, max(60.0, float(dna.get("scores", {}).get("scalability", 75.0))))

        # 4. Risk Exposure (Re)
        # Percent of threats mitigated
        mitigations = len(swot.get("mitigations", []))
        threats = len(swot.get("threats", []))
        risk_exposure = 50.0
        if threats > 0:
            risk_exposure = max(10.0, 100.0 - (mitigations / threats) * 90.0)

        # 5. Strategic Strength (Ss)
        innovation_score = float(dna.get("scores", {}).get("innovation", 80.0))
        strategic_strength = min(100.0, max(50.0, (innovation_score + growth_readiness) / 2))

        # 6. Combined Startup Health Composite Score
        composite_score = (
            (0.25 * execution_readiness) +
            (0.25 * funding_readiness) +
            (0.15 * growth_readiness) +
            (0.15 * (100.0 - risk_exposure)) +
            (0.20 * strategic_strength)
        )

        return StartupHealthIndicators(
            composite_score=round(composite_score, 2),
            execution_readiness=round(execution_readiness, 2),
            funding_readiness=round(funding_readiness, 2),
            growth_readiness=round(growth_readiness, 2),
            risk_exposure=round(risk_exposure, 2),
            strategic_strength=round(strategic_strength, 2)
        )
