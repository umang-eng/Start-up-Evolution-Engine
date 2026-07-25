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
    ConflictResolutionLogItem,
    LegalComplianceDoc,
    FundingSourceRef,
    RegistrationRequirementRef,
    ComplianceDirectoryRef,
    CompetitiveAnalysis,
)
from backend.orchestrator.engine import BaseModule


class BlueprintModule(BaseModule):
    """Analyzes and synthesizes all module outputs into an investor-ready blueprint with competitive analysis."""

    SYSTEM_INSTRUCTION = """You are an elite Principal Strategy Consultant and lead document compiler who prepares business plans for Tier-1 VC firms (Sequoia, Benchmark, a16z). You don't just aggregate data — you analyze it, find patterns, identify risks, and synthesize actionable intelligence.

Your blueprints must demonstrate:
- Deep competitive understanding (not just listing competitors, but analyzing positioning)
- Execution risk awareness (not just listing tasks, but identifying what could go wrong)
- Strategic clarity (not just restating DNA, but providing investment thesis)
- Concrete next steps (not just recommendations, but specific actions with owners and deadlines)"""

    PROMPT_TEMPLATE = """Analyze and synthesize the entire compiled startup profile into an investor-ready blueprint.

Compiled Predecessor Modules:
DNA Profile: {{ dna }}
Product Features: {{ features }}
Delivery Roadmap: {{ roadmap }}
Hiring Chart: {{ team }}
SWOT Analysis: {{ swot }}
Financial Projections: {{ cost }}

Produce a comprehensive analysis (not just aggregation):

1. EXECUTIVE SUMMARY — Write 5 concise, high-impact narrative vectors (2-3 sentences each):
   - Business Summary: problem-solution fit, target audience, business model
   - Strategic Focus: competitive moat, USP, market positioning
   - Execution Plan: feature architecture, MVP milestones, phase timelines
   - Financial Outlook: expenses, scenarios, runway targets
   - Founder Action Plan: critical immediate tasks, risk mitigations

2. COMPETITIVE ANALYSIS — Using DNA competitor data and SWOT analysis:
   - Direct competitors (same problem, same audience)
   - Indirect competitors (adjacent problems)
   - Competitive advantages (where we win)
   - Competitive gaps (where competitors are weak)
   - Differentiation strategy (how to position)

3. MARKET POSITIONING — Write a one-sentence positioning statement using the format:
   "For [target customer] who [need], [product] is a [category] that [benefit]. Unlike [alternative], we [differentiator]."

4. INVESTMENT READINESS CHECKLIST — What's needed before approaching investors:
   - Product milestones (MVP, beta, traction)
   - Business metrics (revenue, users, growth rate)
   - Team gaps (key hires needed)
   - Legal/compliance items

5. KEY ASSUMPTIONS — The 3-5 assumptions that must be true for this business to work

6. NEXT STEPS — Concrete 30-day actions with owners:
   - What specific actions should the founder take?
   - Who owns each action (FOUNDER, CTO, TEAM, ADVISOR)?
   - What's the deadline?

7. EXECUTION RISKS — Top 3-5 risks that could prevent successful execution

8. EXPANSION OPPORTUNITIES — Adjacent markets, verticals, or product extensions

Ensure the output conforms strictly to the requested JSON schema."""

    async def run(
        self,
        db: AsyncSession,
        project: Project,
        context: dict[str, Any],
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
                status_code=400,
            )
        # SWOT is non-critical — use empty dict if missing
        if not swot:
            swot = {"strengths": [], "weaknesses": [], "opportunities": [], "threats": [], "mitigations": [], "founder_actions": []}
            logger.warning("SWOT data missing — using empty defaults for Blueprint composition.")

        # 2. Run Conflict Resolution Engine
        resolved_team, resolved_cost, conflict_logs = self._resolve_conflicts(team, cost)

        # 3. Run Startup Health & Readiness Engine
        health_indicators = self._calculate_health_indicators(dna, features, roadmap, resolved_team, swot, resolved_cost)

        # 4. Invoke Gemini to synthesize narrative Executive Summary + Competitive Analysis
        variables = {
            "dna": dna,
            "features": features,
            "roadmap": roadmap,
            "team": resolved_team,
            "swot": swot,
            "cost": resolved_cost,
        }

        system_instruction, rendered_prompt = self.render_prompt(
            system_template=self.SYSTEM_INSTRUCTION,
            user_template=self.PROMPT_TEMPLATE,
            variables=variables,
        )

        logger.info("Generating narrative Executive Summary + Competitive Analysis...")
        summary_output: ExecutiveSummary = await gemini_adapter.generate(
            prompt=rendered_prompt,
            schema=ExecutiveSummary,
            system_instruction=system_instruction,
        )

        # 5. Build Legal Compliance Doc from context
        legal_compliance_doc = self._build_legal_compliance_doc(context)

        # 6. Build Competitive Analysis from DNA data
        competitive_analysis = self._build_competitive_analysis(dna, swot)

        # 7. Compile final Output Payload
        blueprint_data = BlueprintOutput(
            executive_summary=summary_output,
            startup_dna=dna,
            product_architecture=features,
            execution_roadmap=roadmap,
            team_structure=resolved_team,
            swot_analysis=swot,
            financial_plan=resolved_cost,
            health_indicators=health_indicators,
            conflict_resolution_log=conflict_logs,
            legal_compliance=legal_compliance_doc,
            competitive_analysis=competitive_analysis,
            market_positioning=self._build_positioning_statement(dna),
            investment_readiness_checklist=self._build_investment_checklist(features, roadmap, resolved_team, resolved_cost),
            key_assumptions=dna.get("key_risks", [])[:5],
            next_steps=self._build_next_steps(dna, features, roadmap, resolved_team),
            expansion_opportunities=self._build_expansion_opportunities(dna, features),
            execution_risks=self._build_execution_risks(features, roadmap, resolved_team, swot, resolved_cost),
        )

        output_dict = blueprint_data.model_dump()

        # 8. Persist results in PostgreSQL blueprints table
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
                health_score=health_indicators.composite_score,
            )
            db.add(blueprint_record)

        await db.commit()
        await db.refresh(blueprint_record)

        logger.info(f"Blueprint Composer completed successfully for project: {project.id}")
        return output_dict

    def _build_competitive_analysis(self, dna: dict, swot: dict) -> CompetitiveAnalysis:
        """Build competitive analysis from DNA competitor data and SWOT positioning."""
        competitors = dna.get("competitor_landscape", [])
        direct = [c.get("name", "") for c in competitors if c.get("type", "").lower() == "direct"]
        indirect = [c.get("name", "") for c in competitors if c.get("type", "").lower() in ("indirect", "substitute")]

        strengths = swot.get("strengths", [])
        weaknesses = swot.get("weaknesses", [])

        return CompetitiveAnalysis(
            direct_competitors=direct,
            indirect_competitors=indirect,
            competitive_advantages=strengths[:3],
            competitive_gaps=weaknesses[:3],
            differentiation_strategy=dna.get("usp", ""),
        )

    def _build_positioning_statement(self, dna: dict) -> str:
        """Build a one-sentence positioning statement."""
        segments = dna.get("target_segments", ["customers"])
        target = segments[0] if segments else "customers"
        value = dna.get("value_proposition", "")
        usp = dna.get("usp", "")
        category = dna.get("category", "solution")
        return f"For {target}, {dna.get('business_model', 'solution')} is a {category} that {value}. Unlike alternatives, {usp}."

    def _build_investment_checklist(self, features: dict, roadmap: dict, team: dict, cost: dict) -> list:
        """Build investment readiness checklist from pipeline data."""
        items = []
        feature_count = len(features.get("features", []))
        total_tasks = sum(len(p.get("tasks", [])) for p in roadmap.get("phases", []))
        team_size = team.get("recommended_team_size", 0)
        runway = cost.get("funding_requirements", {}).get("runway_months", 0)

        items.append({"item": f"MVP with {feature_count} features across {len(roadmap.get('phases', []))} phases", "status": "NOT_STARTED", "importance": "CRITICAL"})
        items.append({"item": f"Team of {team_size} roles with hiring sequence defined", "status": "NOT_STARTED", "importance": "HIGH"})
        items.append({"item": f"Financial projections with {runway}-month runway", "status": "NOT_STARTED", "importance": "HIGH"})
        items.append({"item": "Revenue model validated with paying customers", "status": "NOT_STARTED", "importance": "CRITICAL"})
        items.append({"item": "Key hires identified and recruiting pipeline active", "status": "NOT_STARTED", "importance": "HIGH"})
        items.append({"item": "Legal entity established and compliance requirements met", "status": "NOT_STARTED", "importance": "MEDIUM"})
        return items

    def _build_next_steps(self, dna: dict, features: dict, roadmap: dict, team: dict) -> list:
        """Build concrete 30-day next steps."""
        steps = []
        core_features = [f for f in features.get("features", []) if f.get("priority") == "MUST_HAVE"]
        steps.append({
            "action": f"Begin development on {len(core_features)} core features: {', '.join(f.get('name', '') for f in core_features[:3])}",
            "owner": "CTO",
            "deadline": "Week 1-2",
            "priority": "CRITICAL",
            "depends_on": [],
        })
        steps.append({
            "action": "Validate key business assumptions with 10 potential customers",
            "owner": "FOUNDER",
            "deadline": "Week 1-4",
            "priority": "CRITICAL",
            "depends_on": [],
        })
        immediate_hires = [r for r in team.get("org_chart", []) if r.get("hiring_stage") == "Immediate"]
        if immediate_hires:
            steps.append({
                "action": f"Begin recruiting for: {', '.join(r.get('title', '') for r in immediate_hires[:2])}",
                "owner": "FOUNDER",
                "deadline": "Week 2-4",
                "priority": "HIGH",
                "depends_on": [],
            })
        return steps

    def _build_expansion_opportunities(self, dna: dict, features: dict) -> list:
        """Identify expansion opportunities from DNA and features."""
        opportunities = []
        business_model = dna.get("business_model", "")
        if "SaaS" in business_model:
            opportunities.append("Enterprise tier with advanced analytics and API access")
            opportunities.append("White-label solution for larger organizations")
        opportunities.append("Geographic expansion to adjacent markets")
        opportunities.append("Platform ecosystem with third-party integrations")
        return opportunities[:4]

    def _build_execution_risks(self, features: dict, roadmap: dict, team: dict, swot: dict, cost: dict) -> list:
        """Identify top execution risks from pipeline data."""
        risks = []
        total_tasks = sum(len(p.get("tasks", [])) for p in roadmap.get("phases", []))
        high_complexity = [f for f in features.get("features", []) if f.get("complexity") == "HIGH"]
        if len(high_complexity) > 3:
            risks.append(f"High complexity concentration: {len(high_complexity)} features rated HIGH complexity")
        if total_tasks > 30:
            risks.append(f"Large scope: {total_tasks} tasks across {len(roadmap.get('phases', []))} phases may cause timeline slippage")
        team_risks = team.get("key_hiring_risks", [])
        risks.extend(team_risks[:2])
        cost_risks = cost.get("key_cost_risks", [])
        risks.extend(cost_risks[:2])
        threats = swot.get("threats", [])
        risks.extend(threats[:2])
        return risks[:5]

    def _build_legal_compliance_doc(self, context: dict[str, Any]) -> LegalComplianceDoc:
        """Extract and normalize Legal & Compliance data from pipeline context."""
        legal_ctx = context.get("legal_compliance")
        if not legal_ctx:
            return LegalComplianceDoc()

        funding_sources = [
            FundingSourceRef(
                scheme_name=f.get("scheme_name", ""),
                scheme_type=f.get("scheme_type", ""),
                amount_range=f.get("amount_range", ""),
                application_url=f.get("application_url", ""),
                relevance_score=f.get("relevance_score", 0.0),
            )
            for f in legal_ctx.get("funding_sources", [])
        ]

        registration_requirements = [
            RegistrationRequirementRef(
                requirement_name=r.get("requirement_name", ""),
                authority=r.get("authority", ""),
                category=r.get("category", ""),
                is_mandatory=r.get("is_mandatory", False),
                estimated_cost=r.get("estimated_cost", ""),
                priority=r.get("priority", "MEDIUM"),
                reference_url=r.get("reference_url", ""),
            )
            for r in legal_ctx.get("registration_requirements", [])
        ]

        compliance_directories = [
            ComplianceDirectoryRef(
                agency_name=d.get("agency_name", ""),
                jurisdiction=d.get("jurisdiction", ""),
                contact_url=d.get("contact_url", ""),
                relevant_for=d.get("relevant_for", []),
            )
            for d in legal_ctx.get("compliance_directories", [])
        ]

        return LegalComplianceDoc(
            funding_sources=funding_sources,
            registration_requirements=registration_requirements,
            compliance_directories=compliance_directories,
            data_protection_requirements=legal_ctx.get("data_protection_requirements", []),
            summary=legal_ctx.get("summary", ""),
            estimated_compliance_budget_usd=legal_ctx.get("estimated_compliance_budget_usd", 0.0),
        )

    def _resolve_conflicts(
        self,
        team: dict[str, Any],
        cost: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[ConflictResolutionLogItem]]:
        """Applies priority override guidelines (Cost overrides Team values)."""
        conflict_logs: list[ConflictResolutionLogItem] = []
        resolved_team = team.copy()
        resolved_cost = cost.copy()

        org_chart = resolved_team.get("org_chart", [])
        operational_costs = resolved_cost.get("operational_costs", [])

        cost_salaries = {c["category"]: c for c in operational_costs if "salary" in c["category"].lower()}

        for role in org_chart:
            role_id = role["role_id"]
            title = role["title"]
            est_salary = role.get("estimated_salary_usd", 0)

            cost_item_key = f"SALARIES_{role_id.upper()}"
            if cost_item_key in cost_salaries:
                cost_salary_val = cost_salaries[cost_item_key]["monthly_usd"] * 12
                if abs(cost_salary_val - est_salary) > 100:
                    original_val = est_salary
                    resolved_val = cost_salary_val
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
                            log_message=f"Hiring salary for {title} scaled from ${original_val:,.2f} to ${resolved_val:,.2f} to comply with Cost Estimator budget caps.",
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
        cost: dict[str, Any],
    ) -> StartupHealthIndicators:
        """Calculates quantitative startup viability and readiness scores."""
        # 1. Execution Readiness (Er)
        total_tasks = sum(len(p.get("tasks", [])) for p in roadmap.get("phases", []))
        total_features = len(features.get("features", []))
        execution_readiness = 80.0
        if total_features > 0:
            execution_readiness = min(100.0, max(50.0, 50.0 + (total_tasks / total_features) * 10))

        # 2. Funding Readiness (Fr)
        runway_months = cost.get("funding_requirements", {}).get("runway_months", 12)
        funding_readiness = min(100.0, max(40.0, 40.0 + (runway_months / 18.0) * 60.0))

        # 3. Growth Readiness (Gr)
        growth_readiness = min(100.0, max(60.0, float(dna.get("scores", {}).get("scalability", 75.0))))

        # 4. Risk Exposure (Re)
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
            strategic_strength=round(strategic_strength, 2),
        )
